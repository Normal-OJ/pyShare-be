from typing import Callable
import pytest
from tests import utils
from mongo import *


def setup_function(_):
    utils.mongo.drop_db()


def test_add_comment():
    utils.comment.lazy_add_comment()


def test_add_reply():
    utils.comment.lazy_add_reply()


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
