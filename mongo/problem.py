import os
import io
from . import engine
from .engine import GridFSProxy
from .base import MongoBase
from .course import Course
from .user import User
from .utils import doc_required

__all__ = ['Problem']


class Problem(MongoBase, engine=engine.Problem):
    def __init__(self, pid):
        self.pid = pid

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
            _permission.add('d')
        return bool(req & _permission)

    @doc_required('target_course', 'target_course', Course)
    def copy(self, target_course):
        '''
        copy the problem to another course, and drop all comments & replies
        '''
        # serialize
        p = self.to_mongo()
        # delete comments & attachments
        del p['comments']
        del p['attachments']
        # add it to DB
        p = Problem.add(**p)
        # copy files
        attachments = [
            self.new_attatchment(
                filename=a.filename,
                data=a.data.read(),
            ) for a in self.attachments
        ]
        # update info
        p.update(
            attachments=attachments,
            course=target_course.obj,
        )
        return p.reload()

    def delete(self):
        '''
        delete the problem
        '''
        # remove self from course
        self.course.update(pull__problems=self.obj)
        # delete attachments
        for a in self.attachments:
            a.delete()
        # remove problem document
        self.obj.delete()

    def insert_attachment(self, filename, **ks):
        '''
        insert a attahment into this problem.
        ks is the arguments for create a attachment document
        '''
        # check permission
        if any([att.filename == filename for att in self.attachments]):
            raise FileExistsError(
                f'A attachment named [{filename}] '
                'already exists!', )
        # create a new attachment
        att = self.new_attatchment(filename=filename, **ks)
        # push into problem
        problem.update(push__attachments=attachment)

    def remove_attachment(self, name):
        # search by name
        for att in problem.attachments:
            if att.name == name:
                # remove attachment from problem
                self.update(pull__attachments=att)
                # delete it
                att.delete()
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
        qs = {'course': course, 'tags': tags}
        # filter None parameter
        qs = {k: v for k, v in qs.items() if v is None}
        ps = cls.engine.objects(**qs)
        # search for title
        if name is not None:
            ps = ps.search_text(name)
        # retrive fields
        if only is not None:
            ps = ps.only(*only)
        ps = ps.order_by('pid')[offset:]
        count = len(ps) if count != -1 else count
        return ps[:count]

    @classmethod
    def new_attatchment(cls, **ks):
        '''
        create a new attachment, ks will be passed
        to `GridFSProxy`
        '''
        att = GridFSProxy()
        att.put(**ks)
        att.save()
        return att

    @classmethod
    @doc_required('author', 'author', User)
    @doc_required('course', 'course', Course)
    def add(
            cls,
            author: User,
            course: Course,
            tags: list,
            **ks,
    ) -> 'Problem':
        '''
        add a problem to db
        '''
        # student can create problem only in their course
        # but teacher and admin are not limited by this rule
        if author.course != self.course and author < 'teacher':
            raise PermissionError('Not enough permission')
        for tag in tags:
            if not course.check_tag(tag):
                raise TagNotFoundError(
                    'Exist tag that is not allowed to use in this course')
        # insert a new problem into DB
        p = engine.Problem(author=author.obj, **ks)
        p.save()
        # update reference
        course.update(push__problems=p.obj)
        author.update(push__problems=p.obj)
        return cls(p.pid)
