import secrets
import random
from typing import Optional, Union
from mongo import *
from . import course as course_lib
from .utils import drop_none


def data(
    author: Optional[Union[str, User]] = None,
    course: Optional[Union[str, Course]] = None,
    **ks,
):
    if course is None:
        course = course_lib.lazy_add(teacher=author)
    if author is None:
        author = random.choice((
            course.teacher,
            *course.students,
        ))
    ret = {
        'author': author,
        'course': course,
    }
    defaults = {
        'title': lambda: secrets.token_hex(),
        'description': lambda: secrets.token_hex(),
        'default_code': lambda: None,
        'tags': lambda: None,
        'status': lambda: None,
        'is_template': lambda: None,
        'allow_multiple_comments': lambda: None,
    }
    for k, v in defaults.items():
        ret[k] = ks.get(k, v())
    return drop_none(ret)


def lazy_add(**ks):
    return Problem.add(**data(**ks))
