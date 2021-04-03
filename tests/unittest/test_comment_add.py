from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def test_add_comment():
    utils.comment.lazy_add_comment()


def test_add_reply():
    utils.comment.lazy_add_reply()
