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
    def add(cls, author, **ks) -> 'Problem':
        '''
        add a problem to db
        '''
        if user < 'teacher':
            raise PermissionError('Only teacher or admin can create problem!')
        p = engine.Problem(**ks)
        p.save()
        return cls(p.pid)
