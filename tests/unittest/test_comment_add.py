from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def test_add_comment():
    utils.comment.lazy_add_comment()


def test_add_reply():
    utils.comment.lazy_add_reply()


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
