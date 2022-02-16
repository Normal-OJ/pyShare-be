from __future__ import annotations
from datetime import datetime
from typing import Optional, Union
from . import engine
from .course import Course
from .base import MongoBase
from .utils import doc_required
from .event import requirement_added

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
        params = {
            'course': course,
        }
        params = {k: v for k, v in params.items() if v is not None}
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
        params = {
            'course': course.id,
            'title': title,
            'content': content,
            'starts_at': starts_at,
            'ends_at': ends_at,
        }
        params = {k: v for k, v in params.items() if v is not None}
        task = cls.engine(**params).save()
        return cls(task)

    def to_dict(self) -> dict:
        ret = self.to_mongo().to_dict()
        ret['id'] = ret['_id']
        ret['startsAt'] = ret['starts_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
        ret['endsAt'] = ret['ends_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
        for k in ('_id', 'starts_at', 'ends_at'):
            del ret[k]
        return ret
