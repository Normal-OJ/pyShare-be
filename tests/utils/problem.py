import secrets
import random
from typing import Optional, Union
from mongo import *
from . import course as course_lib
from . import user as user_lib
from .utils import drop_none, none_or


def data(
    author: Optional[Union[str, User]] = None,
    course: Optional[Union[str, Course]] = None,
    is_oj: Optional[bool] = None,
    input: Optional[str] = None,
    output: Optional[str] = None,
    **ks,
):
    # Ensure course
    if course is None:
        course = course_lib.lazy_add(teacher=user_lib.Factory.teacher())
    # Randomly pick one from course
    if author is None:
        author = random.choice((
            course.teacher,
            *course.students,
        ))
    ret = {
        'author': author,
        'course': course,
    }
    if is_oj:
        ret.update({
            'extra': {
                '_cls': 'OJProblem',
                'input': none_or(input, secrets.token_hex()),
                'output': none_or(output, secrets.token_hex()),
            },
        })
    defaults = {
        'title': secrets.token_hex(),
        'description': secrets.token_hex(),
        'default_code': None,
        'tags': None,
        'status': None,
        'is_template': None,
        'allow_multiple_comments': None,
    }
    for k, v in defaults.items():
        ret[k] = ks.get(k, v)
    return drop_none(ret)


def lazy_add(**ks):
    return Problem.add(**data(**ks))
