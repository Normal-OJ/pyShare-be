from .base import MongoBase
from .user import User
from . import engine
from .utils import *

__all__ = ['Course']


class Course(MongoBase, engine=engine.Course):
    def __init__(self, name):
        self.name = name

    def check_tag(self, tag):
        return (tag in self.tags)

    @classmethod
    @doc_required('teacher', User)
    def add(cls, teacher, **ks):
        # convert username to user document
        if teacher < 'teacher':
            raise PermissionError(
                'only those who has more permission'
                ' than teacher can create course', )
        # insert a new course into DB
        c = cls.engine(
            teacher=teacher.username,
            **ks,
        )
        c.save()
        # update teacher course
        teacher.update(course=c)
        return cls(c.name)
