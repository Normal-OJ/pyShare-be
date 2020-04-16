from .base import MongoBase
from .user import User
from . import engine

__all__ = ['Course']


class Course(MongoBase, engine=engine.Course):
    def __init__(self, name):
        self.name = name

    def check_tag(self, tag):
        return (tag in self.tags)

    @classmethod
    def add(cls, teacher, **ks):
        # convert username to user document
        if isinstance(teacher, str):
            teacher = User(teacher)
            if not teacher:
                raise engine.DoesNotExist(f'user {teacher} not exist')
        if teacher < 'teacher':
            raise PermissionError(
                'only those who has more permission'
                ' than teacher can create course', )
        c = cls.engine(
            teacher=teacher.username,
            **ks,
        )
        c.save()
        return cls(c.name)
