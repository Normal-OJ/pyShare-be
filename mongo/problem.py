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
    def permission(self, user: User, req):
        _permission = {'r'}
        if user == self.author:
            _permission.add('w')
            _permission.add('d')
        elif user > 'student':
            _permission.add('d')
        return bool(req & _permission)

    def __str__(self):
        return f'problem [{self.pid}]'

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
            engine.Attachment(
                name=a.name,
                data=io.BytesIO(a.data.read()),
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

    def insert_attachment(self, name, **ks):
        '''
        insert a attahment into this problem.
        ks is the arguments for create a attachment document
        '''
        if any([att.name == name for att in self.attachment]):
            raise FileExistsError(
                f'A attachment named [{name}] '
                'already exists!', )
        attachment = engine.Attachment(
            name=name,
            **ks,
        )
        attachment.save()
        problem.update(push__attachments=attachment)

    def remove_attachment(self, name):
        for att in problem.attachments:
            if att.name == name:
                att.delete()
                return True
        raise FileNotFoundError(f'can not find a attachment named [{name}]')

    @classmethod
    def filter(
            cls,
            offset=0,
            count=-1,
            name: str = None,
            tags: list = None,
            only: list = None,
    ) -> 'List[engine.Problem]':
        '''
        read a list of problem filtered by given paramter
        '''
        qs = {'title': name, 'tags': tags}
        # filter None parameter
        qs = {k: v for k, v in qs.items() if v is None}
        ps = cls.engine.objects(**qs)
        # retrive fields
        if only is not None:
            ps = ps.only(*only)
        ps = ps.order_by('pid')[offset:]
        count = len(ps) if count != -1 else count
        return ps[:count]

    @classmethod
    @doc_required('author', 'author', User)
    @doc_required('course', 'course', Course)
    def add(cls, author, tags, **ks) -> 'Problem':
        '''
        add a problem to db
        '''
        if user < 'teacher':
            raise PermissionError('Only teacher or admin can create problem!')
        for tag in tags:
            if tag not in course.tags:
                raise TagNotFoundError(
                    'Exist tag that is not allowed to use in this course')
        p = engine.Problem(**ks)
        p.save()
        return cls(p.pid)
