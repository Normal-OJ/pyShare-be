import secrets
import random
from typing import Union, List
from mongo import *
from mongo import engine
from .utils import none_or
from . import user

__all__ = ('data', 'lazy_add', 'Factory')


def data(
    name: str = None,
    teacher: Union[str, User] = None,
    year: int = None,
    semester: int = None,
    status: int = None,
    tags: List[str] = [],
):
    ret = {
        'name': none_or(name, secrets.token_hex(16)),
        'year': none_or(year, random.randint(109, 115)),
        'semester': none_or(semester, random.randint(1, 2)),
        'status': none_or(status, engine.Course.Status.PUBLIC),
        'tags': tags,
    }
    # save teacher's pk
    if teacher is not None:
        ret['teacher'] = getattr(teacher, 'pk', teacher)
    else:
        # TODO: use enum to define role
        u = user.lazy_signup(role=1)
        ret['teacher'] = u.pk
    return ret


def lazy_add(**ks):
    return Course.add(**data(**ks))


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