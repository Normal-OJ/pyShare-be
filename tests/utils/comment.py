import secrets
from typing import Optional, Union
from bson.objectid import ObjectId
from mongo import *
from .utils import drop_none, none_or
from . import problem as problem_lib
from . import course as course_lib


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
    elif isinstance(problem, int):
        problem = Problem(problem)
    if author is None:
        author = course_lib.student(problem.course)
    ret.update(
        target=problem,
        author=author,
    )
    return drop_none(ret)


def reply_data(
    comment: Optional[Union[Comment, str, ObjectId]] = None,
    author: Optional[Union[User, str]] = None,
    title: Optional[str] = None,
    content: Optional[str] = None,
):
    if comment is None:
        comment = lazy_add_comment()
    if title is None:
        title = f'Reply-{secrets.token_urlsafe(8)}'
    if content is None:
        content = secrets.token_urlsafe()
    if author is None:
        author = course_lib.student(comment.problem.course)
    return {
        'target': getattr(comment, 'pk', comment),
        'author': author,
        'title': title,
        'content': content,
    }


def lazy_add_comment(**ks):
    return Comment.add_to_problem(**comment_data(**ks))


def lazy_add_reply(**ks):
    return Comment.add_to_comment(**reply_data(**ks))