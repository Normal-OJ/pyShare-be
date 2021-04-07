import secrets
import random
from typing import Union, List, Optional
from mongo import *
from mongo import engine
from .utils import none_or
from . import user

__all__ = ('data', 'lazy_add', 'Factory')


def data(
    name: Optional[str] = None,
    teacher: Optional[Union[str, User]] = None,
    year: Optional[int] = None,
    semester: Optional[int] = None,
    status: Optional[int] = None,
    tags: Optional[List[str]] = None,
):
    ret = {
        'name': none_or(name, secrets.token_hex(16)),
        'year': none_or(year, random.randint(109, 115)),
        'semester': none_or(semester, random.randint(1, 2)),
        'status': none_or(status, engine.Course.Status.PUBLIC),
    }
    if tags is not None:
        ret['tags'] = tags
    # save teacher's pk
    if teacher is not None:
        ret['teacher'] = getattr(teacher, 'pk', teacher)
    else:
        u = user.Factory.teacher()
        ret['teacher'] = u.pk
    return ret


def lazy_add(**ks):
    return Course.add(**data(**ks))


def student(course: Course):
    '''
    Create a user with write permission to `course`'s problems
    '''
    if course.status == engine.Course.Status.PUBLIC:
        return user.Factory.student()
    else:
        # TODO: add student to course, it should not be admin here
        return user.Factory.admin()


class Factory:
    @classmethod
    def public(cls):
        return lazy_add(status=engine.Course.Status.PUBLIC)

    @classmethod
    def readonly(cls):
        return lazy_add(status=engine.Course.Status.READONLY)

    @classmethod
    def private(cls):
        return lazy_add(status=engine.Course.Status.PRIVATE)

    @classmethod
    def default(cls):
        return lazy_add()