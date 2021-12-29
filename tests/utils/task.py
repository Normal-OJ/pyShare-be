import secrets
from datetime import datetime
from typing import Optional, Union
from mongo import Task, Course
from mongo import engine
from . import course as course_lib
from .utils import drop_none


def data(
    title: Optional[str] = None,
    content: Optional[str] = None,
    course: Optional[Union[str, Course, engine.Course]] = None,
    starts_at: Optional[datetime] = None,
    ends_at: Optional[datetime] = None,
):
    if course is None:
        course = course_lib.lazy_add()
    if title is None:
        title = secrets.token_hex(16)
    return drop_none({
        'title': title,
        'content': content,
        'starts_at': starts_at,
        'ends_at': ends_at,
        'course': course,
    })


def lazy_add(**ks):
    return Task.add(**data(**ks))
