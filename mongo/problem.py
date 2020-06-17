import os
import io
from functools import reduce
from mongoengine.queryset.visitor import Q
from . import engine
from .engine import GridFSProxy
from .base import MongoBase
from .course import Course
from .user import User
from .utils import doc_required

__all__ = ['Problem']


class Problem(MongoBase, engine=engine.Problem):
    def __init__(self, pid):
        self.pid = int(pid)

    @doc_required('user', 'user', User)
    def permission(self, user: User, req: set):
        '''
        check user's permission, `req` is a set of required
        permissions, currently accept values are {'r', 'w', 'd'}
        represent read and write respectively

        Returns:
            a `bool` value denotes whether user has these
            permissions 
        '''
        _permission = {'r'}
        # problem author can edit, delete problem
        if user == self.author:
            _permission.add('w')
            _permission.add('d')
        # teacher and admin can, too
        elif user > 'student':
            _permission.add('w')
            _permission.add('d')
        elif not self.online:
            _permission.remove('r')
        return bool(req & _permission)

    @doc_required('target_course', 'target_course', Course)
    def copy(self, target_course):
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
                'passed',
        ):
            del p[field]
        # field conversion
        p['default_code'] = p['defaultCode']
        del p['defaultCode']
        del p['_id']
        # add it to DB
        p = Problem.add(**p)
        # update info
        p.update(course=target_course.obj)
        target_course.update(push__problems=p.obj)
        # update attachments
        for att in self.attachments:
            att = self.new_attatchment(
                att,
                filename=att.filename,
            )
            p.attachments.append(att)
            p.save()
        return p.reload()

    # @property
    # def online(self):
    #     return self.status == 1

    def to_dict(self):
        '''
        cast self to python dictionary for serialization
        '''
        ret = self.to_mongo().to_dict()
        ret['pid'] = ret['_id']
        ret['attachments'] = [att.filename for att in self.attachments]
        ret['timestamp'] = ret['timestamp'].timestamp()
        ret['author'] = self.author.info
        ret['comments'] = [str(c) for c in ret['comments']]
        for k in ('_id', 'passed', 'height'):
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
        # check permission
        if any([att.filename == filename for att in self.attachments]):
            raise FileExistsError(
                f'A attachment named [{filename}] '
                'already exists!', )
        # create a new attachment
        att = self.new_attatchment(file_obj, filename=filename)
        # push into problem
        self.attachments.append(att)
        self.save()

    def remove_attachment(self, name):
        # search by name
        for i, att in enumerate(self.attachments):
            if att.name == name:
                # delete it
                att.delete()
                # remove attachment from problem
                # self.update(pull__attachments=att)
                del self.attachments[i]
                self.save()
                return True
        raise FileNotFoundError(f'can not find a attachment named [{name}]')

    @classmethod
    def filter(
            cls,
            offset=0,
            count=-1,
            name: str = None,
            course: str = None,
            tags: list = None,
            only: list = None,
    ) -> 'List[engine.Problem]':
        '''
        read a list of problem filtered by given paramter
        '''
        qs = {'course': course}
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
        return att

    @classmethod
    @doc_required('author', 'author', User)
    @doc_required('course', 'course', Course)
    def add(
            cls,
            author: User,
            course: Course,
            tags: list = [],
            **ks,
    ) -> 'Problem':
        '''
        add a problem to db
        '''
        # student can create problem only in their course
        # but teacher and admin are not limited by this rule
        if course != author.course and author < 'teacher':
            raise PermissionError('Not enough permission')
        for tag in tags:
            if not course.check_tag(tag):
                raise TagNotFoundError(
                    'Exist tag that is not allowed to use in this course')
        # insert a new problem into DB
        p = engine.Problem(
            author=author.pk,
            course=course.pk,
            tags=tags,
            **ks,
        )
        p.save()
        # update reference
        course.update(push__problems=p)
        author.update(push__problems=p)
        return cls(p.pid)
