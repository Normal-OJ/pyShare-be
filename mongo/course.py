import csv
import tempfile
from . import engine
from .base import MongoBase
from .user import User
from .utils import *

__all__ = ['Course']


class Course(MongoBase, engine=engine.Course):
    def check_tag(self, tag):
        return (tag in self.tags)

    @doc_required('user', 'user', User)
    def own_permission(self, user: User):
        '''
        {'r', 'p', 'w'}
        stand for read, participate, modify
        '''
        _permission = set()
        # course's teacher and admins can do anything
        if user == self.teacher or user >= 'admin':
            _permission |= {'r', 'p', 'w'}
        # course's students can participate, or everyone can participate if the course is public
        elif user in self.students or self.status == self.engine.Status.PUBLIC:
            _permission |= {'r', 'p'}
        elif self.status == self.engine.Status.READONLY:
            _permission |= {'r'}
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
        # insert a new course into DB
        c = cls.engine(
            teacher=teacher.pk,
            name=name,
            **ks,
        ).save(force_insert=True)
        # update teacher course
        teacher.update(add_to_set__courses=c)
        return cls(c)

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
            stat = User(u).statistic([self.obj])
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

    def patch_tag(self, push, pop):
        # popped tags have to be removed from problem that is using it
        for p in self.problems:
            p.tags = list(filter(lambda x: x not in pop, p.tags))
            p.save()
        # add pushed tags
        self.tags += push
        # remove popped tags
        self.tags = list(filter(lambda x: x not in pop, self.tags))
        self.save()
