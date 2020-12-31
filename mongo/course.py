import re
import csv
import tempfile
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

    @doc_required('user', 'user', User)
    def permission(self, user: User, req):
        '''
        check user's permission, `req` is a set of required
        permissions, currently accept values are {'r', 'p', 'w'}
        stand for read, participate, modify

        Returns:
            a `bool` value denotes whether user has these
            permissions 
        '''
        _permission = set()
        # course's teacher and admins can do anything
        if user == self.teacher or user >= 'admin':
            _permission |= {'r', 'p', 'w'}
        # course's students can participate, or everyone can participate if the course is public
        elif user in self.students or self.status == engine.CourseStatus.PUBLIC:
            _permission |= {'r', 'p'}
        elif self.status == engine.CourseStatus.READONLY:
            _permission |= {'r'}
        if isinstance(req, set):
            return not bool(req - _permission)
        return req in _permission

    @classmethod
    @doc_required('teacher', User)
    def add(
        cls,
        teacher: User,
        name: str,
        **ks,
    ):
        if teacher < 'teacher':
            raise PermissionError(
                'only those who has more permission'
                ' than teacher can create course', )
        # check course name
        # it can only contain letters, numbers, underscore (_),
        # dash (-) and dot (.), also, it can not be empty
        if not re.match(r'[\w\.\ _\-]+$', name):
            raise ValueError(f'course name ({name}) is invalid')
        # insert a new course into DB
        c = cls.engine(
            teacher=teacher.username,
            name=name,
            **ks,
        )
        c.save(force_insert=True)
        # update teacher course
        teacher.update(add_to_set__courses=c)
        return cls(c.name)

    def statistic_file(self):
        f = tempfile.TemporaryFile('w+')
        statistic_fields = [
            *User('').statistic().keys(),
            'success',
            'fail',
        ]
        statistic_fields.remove('execInfo')
        writer = csv.DictWriter(
            f,
            fieldnames=[
                'username',
                *statistic_fields,
            ],
        )
        writer.writeheader()
        for u in self.students:
            stat = User(u.username).statistic({self.obj})
            # extract exec info
            exec_info = stat.pop('execInfo')
            # update every other info to its length
            stat = {k: len(v) for k, v in stat.items()}
            stat.update({
                k: sum(info[k] for info in exec_info)
                for k in ['success', 'fail']
            })
            writer.writerow({
                **stat,
                **{
                    'username': u.username,
                },
            })
        f.seek(0)
        return f
