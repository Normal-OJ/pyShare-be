import secrets
import random
from typing import Union
from mongo import *
from mongo import engine


def none_or(val, or_val):
    return val if val is not None else or_val


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
            engine.User.objects(role__gt=0).first().username,
        ),
        'year':
        none_or(year, random.randint(109, 115)),
        'semester':
        none_or(semester, random.randint(1, 2)),
        'status':
        none_or(status, engine.CourseStatus.PUBLIC),
    }
    return ret