from typing import (
    Optional,
    Iterable,
    Union,
    List,
)
from datetime import datetime
from mongo import engine
from mongo.task import Task
from mongo.problem import Problem
from mongo.user import User
from mongo.base import MongoBase
from mongo.event import (
    submission_completed,
    requirement_added,
    task_time_changed,
)
from mongo.utils import (
    get_redis_client,
    doc_required,
    drop_none,
)
from .base import default_on_task_time_changed


class SolveOJProblem(MongoBase, engine=engine.SolveOJProblem):
    __initialized = False

    def __new__(cls, pk, *args, **kwargs):
        # TODO: handle rejudge, which might convert a AC submission into WA
        if not cls.__initialized:
            submission_completed.connect(cls.on_submission_completed)
            task_time_changed.connect(cls.on_task_time_changed)
            cls.__initialized = True
        return super().__new__(cls, pk, *args, **kwargs)

    # Declare again because blinker cannot accept `partial` as a reciever
    @classmethod
    def on_task_time_changed(cls, *args, **ks):
        default_on_task_time_changed(cls, *args, **ks)

    @classmethod
    def is_valid_submission(cls, submission):
        return all((
            submission.problem.is_OJ,
            submission.result.judge_result == submission.JudgeResult.AC,
            submission.comment is not None,
        ))

    @classmethod
    def on_submission_completed(cls, submission):
        if not cls.is_valid_submission(submission):
            return
        tasks = Task.filter(course=submission.problem.course)
        reqs = cls.engine.objects(
            task__in=[task.id for task in tasks],
            problems=submission.problem,
        )
        for req in reqs:
            cls(req).add_submission(submission)

    def add_submission(self, submission):
        if not self.is_valid_submission(submission):
            return
        if submission.problem not in self.problems:
            return
        with get_redis_client().lock(f'{self}'):
            self.reload('records')
            user = submission.user
            if self.is_completed(user):
                return
            record = self.get_record(user)
            completes = record.completes
            problem = submission.problem
            if problem in completes:
                return
            completes.append(problem.id)
            if len(completes) >= len(self.problems):
                record.completed_at = datetime.now()
            self.set_record(user, record)

    @classmethod
    @doc_required('task', Task)
    def add(
        cls,
        task: Task,
        problems: List[Problem],
    ):
        if len(problems) == 0:
            raise ValueError('`problems` cannot be empty')
        if any(p not in task.course.problems for p in problems):
            raise ValueError('All problems must belong to the course')
        if any(not p.is_OJ for p in problems):
            raise ValueError('Only accept OJ problem')
        req = cls.engine(
            task=task.id,
            problems=[p.id for p in problems],
        ).save()
        requirement_added.send(req)
        return cls(req)

    def sync(
        self,
        *,
        users: Optional[Iterable[Union[User, str]]] = None,
        starts_at: Optional[datetime] = None,
        ends_at: Optional[datetime] = None,
    ):
        if users is None:
            users = self.task.course.students
        users = [getattr(u, 'id', u) for u in users]
        submissions = engine.Submission.objects(
            **drop_none({
                'problem__in': self.problems,
                'timestamp__gte': starts_at,
                'timestamp__lte': ends_at,
                'user__in': users,
            }))
        for submission in submissions:
            self.add_submission(submission)
