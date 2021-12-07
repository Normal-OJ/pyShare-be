from typing import List, Optional
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


class LeaveComment(MongoBase, engine=engine.LeaveComment):
    __initialized = False

    def __new__(cls, pk, *args, **kwargs):
        if not cls.__initialized:
            on_created = signal('comment_created')
            on_created.connect(cls.on_comment_created)
            cls.__initialized = True
        return super().__new__(cls, pk, *args, **kwargs)

    @classmethod
    def is_valid_comment(cls, comment):
        return comment.is_comment

    @classmethod
    def on_comment_created(cls, comment):
        if not cls.is_valid_comment(comment):
            return
        tasks = Task.filter(course=comment.problem.course)
        reqs = cls.engine.objects(
            task__in=[t.id for t in tasks],
            problem=comment.problem,
        )
        for req in reqs:
            cls(req).add_comment(comment)

    def add_comment(self, comment):
        if not self.is_valid_comment(comment):
            return
        if comment.problem != self.problem:
            return
        with get_redis_client().lock(f'{self}'):
            self.reload('records')
            user = comment.author
            if self.is_completed(user):
                return
            record = self.get_record(user)
            if comment in record.comments:
                return
            record.comments.append(comment.id)
            if len(record.comments) >= self.required_number:
                record.completed_at = datetime.now()
            self.set_record(user, record)

    @classmethod
    @doc_required('problem', Problem)
    @doc_required('task', Task)
    def add(
        cls,
        task: Task,
        problem: Problem,
        required_number: Optional[int] = None,
        acceptance: Optional[int] = None,
    ):
        if problem.is_OJ:
            raise ValueError('Only accept normal problem')
        params = {
            'task': task.id,
            'problem': problem.id,
            'required_number': required_number,
            'acceptance': acceptance,
        }
        params = {k: v for k, v in params.items() if v is not None}
        req = cls.engine(**params).save()
        return cls(req)


class ReplyToComment(MongoBase, engine=engine.ReplyToComment):
    __initialized = False

    def __new__(cls, pk, *args, **kwargs):
        if not cls.__initialized:
            on_created = signal('reply_created')
            on_created.connect(cls.on_reply_created)
            cls.__initialized = True
        return super().__new__(cls, pk, *args, **kwargs)

    @classmethod
    def is_valid_reply(cls, reply):
        return not reply.is_comment

    @classmethod
    def on_reply_created(cls, reply):
        if not cls.is_valid_reply(reply):
            return
        tasks = Task.filter(course=reply.problem.course)
        reqs = cls.engine.objects(task__in=[t.id for t in tasks])
        for req in reqs:
            cls(req).add_reply(reply)

    def add_reply(self, reply):
        with get_redis_client().lock(f'{self}'):
            self.reload('records')
            user = reply.author
            if self.is_completed(user):
                return
            record = self.get_record(user)
            if reply in record.replies:
                return
            record.replies.append(reply.id)
            if len(record.replies) >= self.required_number:
                record.completed_at = datetime.now()
            self.set_record(user, record)

    @classmethod
    @doc_required('task', Task)
    def add(
        cls,
        task: Task,
        required_number: Optional[int] = None,
    ):
        params = {
            'task': task.id,
            'required_number': required_number,
        }
        params = {k: v for k, v in params.items() if v is not None}
        req = cls.engine(**params).save()
        return cls(req)


class LikeOthersComment(MongoBase, engine=engine.LikeOthersComment):
    __initialized = False

    def __new__(cls, pk, *args, **kwargs):
        if not cls.__initialized:
            liked = signal('liked')
            liked.connect(cls.on_liked)
            cls.__initialized = True
        return super().__new__(cls, pk, *args, **kwargs)

    @classmethod
    def is_valid_liker(cls, comment, user):
        return user != comment.author

    @classmethod
    def on_liked(cls, comment, user):
        if not cls.is_valid_liker(comment, user):
            return
        tasks = Task.filter(course=comment.problem.course)
        reqs = cls.engine.objects(task__in=[t.id for t in tasks])
        for req in reqs:
            cls(req).add_like(comment, user)

    def add_like(self, comment, user):
        if not self.is_valid_liker(comment, user):
            return
        with get_redis_client().lock(f'{self}'):
            self.reload('records')
            if self.is_completed(user):
                return
            record = self.get_record(user)
            if comment in record.comments:
                return
            record.comments.append(comment.id)
            if len(record.comments) >= self.required_number:
                record.completed_at = datetime.now()
            self.set_record(user, record)

    @classmethod
    @doc_required('task', Task)
    def add(
        cls,
        task: Task,
        required_number: int,
    ):
        req = cls.engine(
            task=task.id,
            required_number=required_number,
        ).save()
        return cls(req)
