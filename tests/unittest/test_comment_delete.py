from typing import Callable
import pytest
from tests import utils
from mongo import *
from mongo import engine


def setup_function(_):
    utils.mongo.drop_db()


@pytest.mark.parametrize(
    'factory_func',
    [
        utils.comment.lazy_add_comment,
        utils.comment.lazy_add_reply,
    ],
)
def test_delete(factory_func: Callable[[], Comment]):
    c = factory_func()
    assert c.status == engine.Comment.Status.SHOW
    c = c.delete().reload()
    assert c.status == engine.Comment.Status.HIDDEN


def test_delete_tree():
    '''
    delete a comment should also delete all replies
    '''
    c = utils.comment.lazy_add_comment()
    rs = [utils.comment.lazy_add_reply(comment=c) for _ in range(10)]
    # call reload first to ensure that all replies is stored
    c.reload().delete()
    for r in rs:
        r.reload()
    assert all(r.status == engine.Comment.Status.HIDDEN
               for r in rs), [r.status for r in rs]
