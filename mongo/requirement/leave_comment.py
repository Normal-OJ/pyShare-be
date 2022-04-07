from typing import (
    Optional,
    Iterable,
    Union,
)
from datetime import datetime
from mongo import engine
from mongo.task import Task
from mongo.problem import Problem
from mongo.user import User
from mongo.base import MongoBase
from mongo.event import (
    requirement_added,
    comment_created,
    task_time_changed,
)
from mongo.utils import (
    get_redis_client,
    doc_required,
    drop_none,
    logger,
)
from .base import default_on_task_time_changed


class LeaveComment(MongoBase, engine=engine.LeaveComment):
    __initialized = False

    def __new__(cls, *args, **kwargs):
        cls.register_event_listener()
        return super().__new__(cls, *args, **kwargs)

    @classmethod
    def register_event_listener(cls):
        if cls.__initialized:
            return
        cls.__initialized = True
        comment_created.connect(cls.on_comment_created)
        task_time_changed.connect(cls.on_task_time_changed)
        logger().info(f'Event listener registered [class={cls.__name__}]')

    # Declare again because blinker cannot accept `partial` as a reciever
    @classmethod
    def on_task_time_changed(cls, *args, **ks):
        default_on_task_time_changed(cls, *args, **ks)

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
        requirement_added.send(req)
        logger().info(f'Requirement created [requirement={req.id}]')
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
        comments = engine.Comment.objects(**drop_none({
            'problem': self.problem,
            'author__in': users,
            'created__gte': starts_at,
            'created__lte': ends_at,
        }))
        for comment in comments:
            self.add_comment(comment)


LeaveComment.register_event_listener()
