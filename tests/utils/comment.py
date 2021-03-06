import secrets
from typing import Optional, Union
from mongo import *
from mongo import engine
from .utils import drop_none, none_or
from . import user as user_lib
from . import problem as problem_lib


def comment_data(
    title: Optional[str] = None,
    content: Optional[str] = None,
    author: Optional[Union[User, str]] = None,
    problem: Optional[Union[Problem, int]] = None,
    code: Optional[str] = None,
):
    ret = {
        'title': none_or(title, secrets.token_hex()),
        'content': none_or(content, secrets.token_hex()),
        'code': none_or(code, "print('kon peko kon peko')"),
    }
    if problem is None:
        problem = problem_lib.lazy_add()
    if author is None:
        # generate a user has write permission to the problem
        course = problem.course
        if course.status == engine.CourseStatus.PUBLIC:
            author = user_lib.Factory.student()
        else:
            # TODO: add student to course, it should not be admin here
            author = user_lib.Factory.admin()
    ret.update(
        target=problem,
        author=author,
    )
    return drop_none(ret)


def lazy_add_comment(**ks):
    Comment.add_to_problem(**comment_data(**ks))
