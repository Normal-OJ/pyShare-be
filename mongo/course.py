import re
import io
import csv
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
    def add(
        cls,
        teacher: User,
        name: str,
        **ks,
    ):
        # convert username to user document
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
        c.save()
        # update teacher course
        teacher.update(add_to_set__courses=c)
        return cls(c.name)

    def statistic_file(self):
        f = io.StringIO()
        statistic_fields = list(User('').statistic().keys())
        writer = csv.DictWriter(
            f,
            fieldnames=[
                'username',
                *statistic_fields,
            ],
        )
        writer.writeheader()
        for u in self.students:
            stat = User(u.username).statistic()
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
        return f
