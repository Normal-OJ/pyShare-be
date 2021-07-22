from typing import List, Optional
from functools import reduce
from mongoengine.queryset.visitor import Q
from . import engine
from .engine import GridFSProxy
from .base import MongoBase
from .course import Course
from .user import User
from .utils import doc_required

__all__ = ['Problem', 'TagNotFoundError']


class TagNotFoundError(Exception):
    pass


class Problem(MongoBase, engine=engine.Problem):
    @doc_required('user', 'user', User)
    def own_permission(self, user: User):
        '''
        {'r', 'w', 'd', 'c'}
        represent read, write, delete, clone respectively
        '''
        _permission = set()
        if self.online:
            if Course(self.course).permission(user=user, req={'r'}):
                _permission.add('r')
        elif user == self.course.teacher:
            _permission.add('r')
        # all templates can be used
        if self.is_template:
            _permission.add('r')
        # problem author and admin can edit, delete problem
        if user == self.author or user >= 'admin':
            _permission |= {*'rwd'}
        # teachers and above can clone
        if user >= 'teacher':
            _permission.add('c')
        return _permission

    @doc_required('user', 'user', User)
    def permission(self, user: User, req):
        '''
        check user's permission, `req` is a set of required
        permissions

        Returns:
            a `bool` value denotes whether user has these
            permissions 
        '''
        _permission = self.own_permission(user=user)
        if isinstance(req, set):
            return not bool(req - _permission)
        return req in _permission

    @doc_required('target_course', 'target_course', Course)
    def copy(self, target_course: Course, is_template: bool):
        '''
        copy the problem to another course, and drop all comments & replies
        '''
        # serialize
        p = self.to_mongo()
        # delete non-shared datas
        for field in (
                'comments',
                'attachments',
                'height',
        ):
            del p[field]
        # field conversion
        p['default_code'] = p['defaultCode']
        p['is_template'] = is_template
        p['allow_multiple_comments'] = p['allowMultipleComments']
        del p['defaultCode']
        del p['isTemplate']
        del p['allowMultipleComments']
        del p['_id']
        # add it to DB
        p = Problem.add(**p)
        # update info
        p.update(course=target_course.obj)
        target_course.update(push__problems=p.obj)
        # update attachments
        for att in self.attachments:
            att = self.new_attatchment(
                att.file,
                filename=att.filename,
            )
            p.attachments.append(att)
            p.save()
        return p.reload()

    @property
    def online(self):
        return self.status == 1

    def to_dict(self):
        '''
        cast self to python dictionary for serialization
        '''
        ret = self.to_mongo().to_dict()
        ret['pid'] = ret['_id']
        ret['course'] = str(ret['course'])
        ret['attachments'] = [att.filename for att in self.attachments]
        ret['timestamp'] = ret['timestamp'].timestamp()
        ret['author'] = self.author.info
        ret['comments'] = [str(c) for c in ret['comments']]
        for k in ('_id', 'height'):
            del ret[k]
        return ret

    def delete(self):
        '''
        delete the problem
        '''
        # delete attachments
        for a in self.attachments:
            a.delete()
        # remove problem document
        self.obj.delete()

    def insert_attachment(self, file_obj, filename):
        '''
        insert a attahment into this problem.
        '''
        # check existence
        if any([att.filename == filename for att in self.attachments]):
            raise FileExistsError(
                f'A attachment named [{filename}] '
                'already exists!', )
        # create a new attachment
        att = self.new_attatchment(file_obj, filename=filename)
        # push into problem
        self.attachments.append(att)
        self.save()

    def remove_attachment(self, filename):
        '''
        Remove a attachment by filename.
        Due to the mongoengine's bug, we can not use pull
        operator here, this may cause race condition. DON'T
        call this concurrently.
        '''
        # search by name
        for i, att in enumerate(self.attachments):
            if att.filename == filename:
                # delete it and pop from list
                att.delete()
                self.attachments.pop(i)
                self.save()
                return True
        raise FileNotFoundError(
            f'can not find a attachment named [{filename}]')

    @classmethod
    def filter(
        cls,
        offset=0,
        count=-1,
        name: Optional[str] = None,
        course: Optional[str] = None,
        tags: Optional[List[str]] = None,
        only: Optional[List[str]] = None,
        is_template: Optional[bool] = None,
        allow_multiple_comments: Optional[bool] = None,
    ) -> List[engine.Problem]:
        '''
        read a list of problem filtered by given paramter
        '''
        qs = {
            'course': course,
            'is_template': is_template,
            'allow_multiple_comments': allow_multiple_comments,
        }
        # filter None parameter
        qs = {k: v for k, v in qs.items() if v is not None}
        ps = cls.engine.objects(**qs)
        # filter tags
        if tags is not None:
            ps = ps.filter(
                reduce(
                    lambda x, y: x & y,
                    (Q(tags=t) for t in tags),
                ))
        # search for title
        if name is not None:
            ps = ps.filter(title__icontains=name)
        # retrive fields
        if only is not None:
            ps = ps.only(*only)
        ps = ps.order_by('pid')[offset:]
        count = len(ps) if count == -1 else count
        return ps[:count]

    @classmethod
    def new_attatchment(cls, file_obj, **ks):
        '''
        create a new attachment, ks will be passed
        to `GridFSProxy`
        '''
        att = GridFSProxy()
        att.put(file_obj, **ks)
        return engine.Problem.ProblemAttachment(file=att)

    @classmethod
    @doc_required('author', 'author', User)
    @doc_required('course', 'course', Course)
    def add(
            cls,
            author: User,
            course: Course,
            tags: List[str] = [],
            **ks,
    ) -> 'Problem':
        '''
        add a problem to db
        '''
        # user needs to be able to modify the course
        if not course.permission(user=author, req={'p'}):
            raise PermissionError('Not enough permission')
        # if allow_multiple_comments is None or False
        if author < 'teacher' and not ks.get('allow_multiple_comments'):
            raise PermissionError('Students have to allow multiple comments')
        if not all(course.check_tag(tag) for tag in tags):
            raise TagNotFoundError(
                'Exist tag that is not allowed to use in this course')
        # insert a new problem into DB
        p = cls.engine(
            author=author.pk,
            course=course.pk,
            tags=tags,
            **ks,
        ).save()
        # update reference
        course.update(push__problems=p)
        author.update(push__problems=p)
        return cls(p)
