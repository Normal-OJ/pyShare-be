from typing import Callable
import concurrent.futures
import pytest
from tests import utils
from mongo import *


def setup_function(_):
    utils.mongo.drop_db()


def test_add_comment():
    utils.comment.lazy_add_comment()


def test_add_comment_multiple():
    cnt = 5
    p = utils.problem.lazy_add()
    # Sequentially add
    cs = [utils.comment.lazy_add_comment(problem=p.pk) for _ in range(cnt)]
    p.reload('comments')
    c_ids = [c.id for c in cs]
    p_ids = [c.id for c in p.comments]
    # Check all comments are inserted to the right location
    assert c_ids == p_ids
    # Cehck floor numbers
    assert [c.floor for c in cs] == [*range(1, cnt + 1)]


def test_add_reply():
    c = utils.comment.lazy_add_comment()
    # sequentially add
    for _ in range(5):
        r = utils.comment.lazy_add_reply(comment=c.pk)
        assert r.obj in c.reload('replies').replies


def test_add_reply_concurrent():
    c = utils.comment.lazy_add_comment()
    cnt = 10
    # Concurrently create new replies
    with concurrent.futures.ThreadPoolExecutor() as executor:
        create_reply = lambda _c: utils.comment.lazy_add_reply(comment=_c)
        results = [*executor.map(
            create_reply,
            (c for _ in range(cnt)),
        )]
    r_ids = sorted(r.id for r in results)
    c_ids = sorted(r.id for r in c.reload('replies').replies)
    # Check all the inserted replies are put under the comment
    assert r_ids == c_ids


def test_add_comment_concurrent():
    p = utils.problem.lazy_add()
    cnt = 10
    # Concurrently create new replies
    with concurrent.futures.ThreadPoolExecutor() as executor:
        create_reply = lambda _p: utils.comment.lazy_add_comment(problem=_p.pk)
        results = [*executor.map(
            create_reply,
            (p for _ in range(cnt)),
        )]
    r_ids = sorted(c.id for c in results)
    c_ids = sorted(c.id for c in p.reload('comments').comments)
    # Check all the inserted replies are put under the comment
    assert r_ids == c_ids
    # Check floor number
    assert sorted(r.floor for r in results) == [*range(1, cnt + 1)]


# TODO: put these functions not related to add to right location


def test_like_comment():
    c = utils.comment.lazy_add_comment()
    # ensure this user has permission to like comment
    u = utils.course.student(c.problem.course)
    assert c.obj not in u.likes
    assert u.obj not in c.liked
    c.like(user=u)
    u.reload()
    assert c.obj in u.likes
    assert u.obj in c.liked


@pytest.mark.parametrize(
    'factory_func',
    [
        utils.comment.lazy_add_comment,
        utils.comment.lazy_add_reply,
    ],
)
def test_to_dict(factory_func: Callable[[], Comment]):
    c = factory_func()
    d = c.to_dict()
    excepted_keys = [
        'created',
        'updated',
        'submission',
        'submissions',
        'author',
        'replies',
        'liked',
    ]
    # check fields
    assert all(k in d for k in excepted_keys), d.keys()
    # TODO: validate response content
