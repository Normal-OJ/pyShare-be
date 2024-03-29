from __future__ import annotations
import csv
import tempfile
import enum
from typing import List, TYPE_CHECKING, Set, Union
from . import engine
from .base import MongoBase
from .user import User
from .utils import *

__all__ = ['Course']

if TYPE_CHECKING:
    from .problem import Problem


class Course(MongoBase, engine=engine.Course):
    class Permission(enum.Flag):
        READ = enum.auto()
        WRITE = enum.auto()
        PARTICIPATE = enum.auto()

    def get_tags_by_category(self, category) -> List[str]:
        tags = {
            engine.Tag.Category.COURSE: self.tags,
            engine.Tag.Category.NORMAL_PROBLEM: self.normal_problem_tags,
            engine.Tag.Category.OJ_PROBLEM: self.OJ_problem_tags,
        }.get(category, None)
        if tags is None:
            raise ValueError('invalid category')
        return tags

    def check_tag(self, tag, category):
        from .tag import Tag
        if not Tag.is_tag(tag, category):
            return False
        tags = self.get_tags_by_category(category)
        return (tag in tags)

    @doc_required('user', User)
    def own_permission(self, user: User) -> 'Course.Permission':
        _permission = self.Permission(0)
        # course's teacher and admins can do anything
        if user == self.teacher or user >= 'admin':
            _permission |= ( \
                self.Permission.READ |
                self.Permission.WRITE |
                self.Permission.PARTICIPATE
            )
        # course's students can participate, or everyone can participate if the course is public
        elif user in self.students or self.status == self.engine.Status.PUBLIC:
            _permission |= (self.Permission.READ | self.Permission.PARTICIPATE)
        elif self.status == self.engine.Status.READONLY:
            _permission |= self.Permission.READ
        return _permission

    @doc_required('user', 'user', User)
    def permission(self, user: User, req: 'Course.Permission') -> bool:
        '''
        check user's permission, `req` is a set of required
        permissions
        
        Returns:
            a `bool` value denotes whether user has these
            permissions 
        '''
        _permission = self.own_permission(user=user)
        return bool(req & _permission)

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
        from .tag import Tag
        if teacher < 'teacher':
            raise PermissionError(
                'only those who has more permission'
                ' than teacher can create course', )
        # Tags should exist in collection
        if not all(map(Tag.is_course_tag, ks.get('tags', []))):
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

    def push_tags(self, tags: List[str], category: int):
        self.patch_tag(push=tags, category=category)

    def pull_tags(self, tags: List[str], category: int):
        self.patch_tag(pop=tags, category=category)

    def patch_tag(
        self,
        push: List[str] = [],
        pop: List[str] = [],
        category: int = engine.Tag.Category.NORMAL_PROBLEM,
    ):
        from .tag import Tag
        tags = self.get_tags_by_category(category)
        if not all(Tag.is_tag(tag, category) for tag in push + pop):
            raise Tag.engine.DoesNotExist(
                'Some tag can not be '
                'found in system', )
        if {*pop} & {*push}:
            raise ValueError('Tag appears in both list')
        if {*push} & {*tags}:
            raise ValueError('Some pushed tags are already in course')
        if not {*pop} <= {*tags}:
            raise ValueError('Some popped tags are not in course')
        # popped tags have to be removed from problem that is using it
        if category == engine.Tag.Category.OJ_PROBLEM or category == engine.Tag.Category.NORMAL_PROBLEM:
            for p in self.problems:
                if category == p.tag_category:
                    p.tags = list(filter(lambda x: x not in pop, p.tags))
                    p.save()
        # add pushed tags
        tags += push
        # remove popped tags
        # this will modify the original list without assigning to a new one
        tags[:] = list(filter(lambda x: x not in pop, tags))
        self.save()
