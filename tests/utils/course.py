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
    normal_problem_tags: Optional[List[str]] = None,
    OJ_problem_tags: Optional[List[str]] = None,
):
    ret = {
        'name': none_or(name, secrets.token_hex(16)),
        'year': none_or(year, random.randint(109, 115)),
        'semester': none_or(semester, random.randint(1, 2)),
        'status': none_or(status, engine.Course.Status.PUBLIC),
    }
    if tags is not None:
        ret['tags'] = tags
    if normal_problem_tags is not None:
        ret['normal_problem_tags'] = normal_problem_tags
    if OJ_problem_tags is not None:
        ret['OJ_problem_tags'] = OJ_problem_tags
    # Save teacher's pk
    if teacher is not None:
        ret['teacher'] = getattr(teacher, 'pk', teacher)
    else:
        u = user.Factory.teacher()
        ret['teacher'] = u.pk
    return ret


def lazy_add(
    auto_insert_tags: bool = False,
    **ks,
):
    course_data = data(**ks)
    if auto_insert_tags == True:
        for tag in course_data.get('tags', []):
            Tag.add(tag, engine.Tag.Category.COURSE)
        for tag in course_data.get('normal_problem_tags', []):
            Tag.add(tag, engine.Tag.Category.NORMAL_PROBLEM)
        for tag in course_data.get('OJ_problem_tags', []):
            Tag.add(tag, engine.Tag.Category.OJ_PROBLEM)
    return Course.add(**course_data)


@doc_required('course', Course)
def student(course: Course):
    '''
    Create a user with participate permission to `course`'s problems
    '''
    u = user.Factory.student()
    course.add_student(u)
    return u


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
