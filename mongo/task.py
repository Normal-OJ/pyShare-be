from __future__ import annotations
from datetime import datetime
from typing import Optional, Union
from . import engine
from .course import Course
from .base import MongoBase
from .utils import doc_required


class Task(MongoBase, engine=engine.Task):
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
        starts_at: Optional[datetime] = None,
        ends_at: Optional[datetime] = None,
    ):
        params = {
            'course': course.id,
            'starts_at': starts_at,
            'ends_at': ends_at,
        }
        params = {k: v for k, v in params.items() if v is not None}
        task = cls.engine(**params).save()
        return cls(task)
