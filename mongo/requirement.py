from typing import List
from blinker import signal
from datetime import datetime
from . import engine
from .base import MongoBase
from .task import Task
from .problem import Problem
from .utils import doc_required, get_redis_client


class SolveOJProblem(MongoBase, engine=engine.SolveOJProblem):
    __initialized = False

    def __new__(cls, pk, *args, **kwargs):
        # TODO: handle rejudge, which might convert a AC submission into WA
        if not cls.__initialized:
            on_completed = signal('submission_completed')
            on_completed.connect(cls.on_submission_completed)
            cls.__initialized = True
        return super().__new__(cls, pk, *args, **kwargs)

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
            if self.is_completed(submission.user):
                return
            username = submission.user.username
            record = self.records.get(
                username,
                self.engine.Record(),
            )
            completes = record.completes
            problem = submission.problem
            if problem not in completes:
                completes.append(problem)
            if len(completes) == len(self.problems):
                record.completed_at = datetime.now()
            self.update(**{f'records__{username}': record})

    @classmethod
    @doc_required('task', Task)
    def add(
        cls,
        task: Task,
        problems: List[Problem],
    ):
        if len(problems) < 0:
            raise ValueError('`problems` cannot be empty')
        if any(p not in task.course.problems for p in problems):
            raise ValueError('All problems must belong to the course')
        if any(not p.is_OJ for p in problems):
            raise ValueError('Only accept OJ problem')
        req = cls.engine(
            task=task.id,
            problems=[p.id for p in problems],
        ).save()
        return cls(req)
