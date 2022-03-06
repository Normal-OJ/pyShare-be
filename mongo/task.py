from __future__ import annotations
from datetime import datetime
from typing import Optional, Union
import copy
from contextlib import contextmanager
from . import engine
from .course import Course
from .base import MongoBase
from .utils import (
    doc_required,
    get_redis_client,
    drop_none,
)
from .event import (task_due_extended, requirement_added, task_time_changed)

__all__ = ['Task']


class Task(MongoBase, engine=engine.Task):
    __initialized = False

    def __new__(cls, pk, *args, **kwargs):
        if not cls.__initialized:
            requirement_added.connect(cls.on_requirement_added)
            cls.__initialized = True
        return super().__new__(cls, pk, *args, **kwargs)

    @classmethod
    def on_requirement_added(cls, requirement):
        requirement.task.update(push__requirements=requirement)

    @classmethod
    def filter(
        cls,
        course: Optional[Union[Course, str]] = None,
    ):
        if isinstance(course, Course):
            course = course.id
        params = drop_none({'course': course})
        tasks = [cls(t) for t in cls.engine.active_objects(**params)]
        return tasks

    @classmethod
    @doc_required('course', Course)
    def add(
        cls,
        course: Course,
        title: str,
        content: Optional[str] = None,
        starts_at: Optional[datetime] = None,
        ends_at: Optional[datetime] = None,
    ):
        params = drop_none({
            'course': course.id,
            'title': title,
            'content': content,
            'starts_at': starts_at,
            'ends_at': ends_at,
        })
        task = cls.engine(**params).save()
        return cls(task)

    def to_dict(self) -> dict:
        ret = self.to_mongo().to_dict()
        ret['id'] = ret.pop('_id')
        ret['startsAt'] = ret.pop('starts_at').strftime('%Y-%m-%dT%H:%M:%SZ')
        ret['endsAt'] = ret.pop('ends_at').strftime('%Y-%m-%dT%H:%M:%SZ')
        return ret

    def __deepcopy__(self, _):
        '''
        Copy a new task and save it into DB.
        '''
        new_task = copy.copy(self.obj)
        new_task.id = None
        requirements = new_task.requirements
        new_task.requirements = None
        # Call save first to generate id for task
        new_task.save()
        for req in requirements:
            req.id = None
            req.task = new_task
            req.save()
        # Save requirements
        new_task.update(requirements=requirements)
        return Task(new_task.reload())

    @contextmanager
    def tmp_copy(self):
        '''
        Return a context of temprory copy of original task.
        Which will be deleted after exiting context.
        '''
        tmp = copy.deepcopy(self)
        yield tmp
        tmp.delete()

    def extend_due(self, ends_at: datetime):
        with get_redis_client().lock(f'{self}'):
            if ends_at < self.ends_at:
                return
            # Update field
            starts_at = self.ends_at
            self.ends_at = ends_at
            self.save()
            # Add reload to ensure the requirements field is up-to-date
            self.reload('requirements')
            task_due_extended.send(self, starts_at=starts_at)
            self.reload('requirements')

    def edit(self, **ks):
        old_starts_at = self.starts_at
        old_ends_at = self.ends_at
        self.update(**ks)
        self.reload()
        if old_starts_at != self.starts_at or old_ends_at != self.ends_at:
            task_time_changed.send(
                self,
                old_starts_at=old_starts_at,
                old_ends_at=old_ends_at,
            )
            self.reload('requirements')
