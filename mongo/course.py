from __future__ import annotations
import csv
import tempfile
from typing import List, TYPE_CHECKING
from . import engine
from .base import MongoBase
from .user import User
from .utils import *
from .tag import Tag

__all__ = ['Course']

if TYPE_CHECKING:
    from .problem import Problem


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

    def add_student(self, user: User):
        user.update(add_to_set__courses=self.obj)
        self.update(add_to_set__students=user.obj)
        return self.reload('students')

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
        # Tags should exist in collection
        if 'tags' in ks and not all(map(Tag, ks['tags'])):
            raise Tag.engine.DoesNotExist(
                'Some tag can not be '
                'found in system', )
        # insert a new course into DB
        c = cls.engine(
            teacher=teacher.pk,
            name=name,
            **ks,
        ).save(force_insert=True)
        # update teacher course
        teacher.update(add_to_set__courses=c)
        return cls(c)

    @classmethod
    def get_by_name(cls, name: str) -> 'Course':
        return cls(cls.engine.objects.get(name=name))

    def statistic_file(self):
        f = tempfile.TemporaryFile('w+')
        statistic_fields = [
            *User('0' * 24).statistic().keys(),
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

    # FIXME: This method may has performance issue
    def oj_statistic(self, problems: List[Problem]):
        student_stats = [{
            'info': s.info,
            **s.oj_statistic(problems)
        } for s in map(User, self.students)]
        overview = {}
        for problem in problems:
            p_stat = {
                'tryCount': 0,
                'acUser': 0,
                'tryUser': 0,
            }
            p_stat['acCount'] = len(
                engine.Submission.objects(
                    problem=problem.pk,
                    result__judge_result=0,  # AC
                ))
            for s_stat in student_stats:
                s_stat = s_stat[str(problem.pid)]
                p_stat['tryCount'] += s_stat['tryCount']
                is_ac = s_stat['result'] == User.OJProblemResult.PASS
                p_stat['acUser'] += is_ac
                tried = s_stat['result'] != User.OJProblemResult.NO_TRY
                p_stat['tryUser'] += tried
            overview[str(problem.pid)] = p_stat
        return {
            'overview': overview,
            'users': student_stats,
        }

    def push_tags(self, tags: List[str]):
        self.patch_tag(push=tags)

    def pull_tags(self, tags: List[str]):
        self.patch_tag(pop=tags)

    def patch_tag(
        self,
        push: List[str] = [],
        pop: List[str] = [],
    ):
        if not all(map(Tag, push + pop)):
            raise Tag.engine.DoesNotExist(
                'Some tag can not be '
                'found in system', )
        if {*pop} & {*push}:
            raise ValueError('Tag appears in both list')
        if {*push} & {*self.tags}:
            raise ValueError('Some pushed tags are already in course')
        if not {*pop} <= {*self.tags}:
            raise ValueError('Some popped tags are not in course')
        # popped tags have to be removed from problem that is using it
        for p in self.problems:
            p.tags = list(filter(lambda x: x not in pop, p.tags))
            p.save()
        # add pushed tags
        self.tags += push
        # remove popped tags
        self.tags = list(filter(lambda x: x not in pop, self.tags))
        self.save()
