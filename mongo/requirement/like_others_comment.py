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
    comment_liked,
    task_time_changed,
)
from mongo.utils import (
    get_redis_client,
    doc_required,
    logger,
)
from .base import default_on_task_time_changed


class LikeOthersComment(MongoBase, engine=engine.LikeOthersComment):
    __initialized = False

    def __new__(cls, *args, **kwargs):
        cls.register_event_listener()
        return super().__new__(cls, *args, **kwargs)

    @classmethod
    def register_event_listener(cls):
        if cls.__initialized:
            return
        cls.__initialized = True
        comment_liked.connect(cls.on_liked)
        task_time_changed.connect(cls.on_task_time_changed)
        logger().debug(f'Event listener registered [class={cls.__name__}]')

    # Declare again because blinker cannot accept `partial` as a reciever
    @classmethod
    def on_task_time_changed(cls, *args, **ks):
        default_on_task_time_changed(cls, *args, **ks)

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
        requirement_added.send(req)
        logger().info(f'Requirement created [requirement={req.id}]')
        return cls(req)

    def sync(
        self,
        *,
        users: Optional[Iterable[Union[User, str]]] = None,
        starts_at: Optional[datetime] = datetime.min,
        ends_at: Optional[datetime] = datetime.max,
    ):
        if users is None:
            users = self.task.course.students
        users = [getattr(u, 'id', u) for u in users]
        for user in map(User, users):
            for comment in user.likes:
                # FIXME: Should check when the user like this comment
                #   instead of when the comment was created
                if starts_at < comment.created < ends_at:
                    self.add_like(comment, user)


LikeOthersComment.register_event_listener()
