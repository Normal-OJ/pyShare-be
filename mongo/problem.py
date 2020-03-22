import os
from . import 
from .engine import GridFSProxy
from .base import MongoBase
from .course import Course
from .utils import doc_required

__all__ = ['Problem']


class Problem(MongoBase, engine=engine.Problem):
    def __init__(self, pid):
        self.pid = pid

    @doc_required('target_course', 'target_course', Course)
    def copy(self, target_course):
        '''
        copy the problem to another course, and drop all comments & replies
        '''
        # serialize
        p = self.to_mongo()
        # copy files
        p['attatchments'] = [*map(GridFSProxy, p['attatchments'])]
        # delete comments
        del p['comments']
        # add it to DB
        return Problem.add(**p)

    def permission(self, user):
        '''
        check the user's permission of this problem
        '''
        pass

    @classmethod
    def filter(
            cls,
            offset=0,
            count=-1,
            name: str = None,
            tags: list = None,
    ) -> 'List[engine.Problem]':
        '''
        read a list of problem filtered by given paramter
        '''
        qs = {'title': name, 'tags': tags}
        # filter None parameter
        qs = {k: v for k, v in qs.items() if v is None}
        ps = cls.engine.objects(**qs).order_by('pid')[offset:]
        count = len(ps) if count != -1 else count
        return ps[:count]

    @classmethod
    def add(cls, **ks) -> 'Problem':
        '''
        add a problem to db
        '''
        p = engine.Problem(**ks)
        p.save()
        return cls(p.pid)

    def delete(self) -> engine.Problem:
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
