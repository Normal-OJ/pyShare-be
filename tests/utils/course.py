import secrets
import random
from typing import Union
from mongo import *
from mongo import engine
from .utils import none_or


def data(
    name: str = None,
    teacher: Union[str, User] = None,
    year: int = None,
    semester: int = None,
    status: int = None,
):
    ret = {
        'name':
        none_or(name, secrets.token_hex(16)),
        'teacher':
        none_or(
            teacher,
            engine.User.objects(role__lt=2).first().username,
        ),
        'year':
        none_or(year, random.randint(109, 115)),
        'semester':
        none_or(semester, random.randint(1, 2)),
        'status':
        none_or(status, engine.CourseStatus.PUBLIC),
    }
    return ret


def random_add(**ks):
    return Course.add(**data(**ks))
