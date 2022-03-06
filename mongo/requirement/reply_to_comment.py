from typing import (
    Optional,
    Iterable,
    Union,
)
from datetime import datetime
from mongo import engine
from mongo.task import Task
from mongo.user import User
from mongo.base import MongoBase
from mongo.event import (
    requirement_added,
    reply_created,
    task_time_changed,
)
from mongo.utils import (
    get_redis_client,
    doc_required,
    drop_none,
)
from .base import default_on_task_time_changed


class ReplyToComment(MongoBase, engine=engine.ReplyToComment):
    __initialized = False

    def __new__(cls, pk, *args, **kwargs):
        if not cls.__initialized:
            reply_created.connect(cls.on_reply_created)
            task_time_changed.connect(cls.on_task_time_changed)
            cls.__initialized = True
        return super().__new__(cls, pk, *args, **kwargs)

    # Declare again because blinker cannot accept `partial` as a reciever
    @classmethod
    def on_task_time_changed(cls, *args, **ks):
        default_on_task_time_changed(cls, *args, **ks)

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
        replies = engine.Comment.objects(**drop_none({
            'author__in': users,
            'depth__ne': 0,
            'created__gte': starts_at,
            'created__lte': ends_at,
        }))
        for reply in replies:
            self.add_reply(reply)
