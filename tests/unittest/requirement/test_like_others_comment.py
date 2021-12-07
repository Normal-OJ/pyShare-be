import pytest
from tests import utils
from mongo import (
    requirement,
    Course,
    ISandbox,
    Task,
)


def setup_function(_):
    ISandbox.use(utils.submission.MockSandbox)


def teardown_function(_):
    ISandbox.use(None)
    utils.mongo.drop_db()


def test_can_count_like_others():
    comment = utils.comment.lazy_add_comment()
    course = Course(comment.problem.course)
    task = Task.add(course=course)
    req = requirement.LikeOthersComment.add(
        task=task,
        required_number=1,
    )
    liker = utils.user.Factory.student()
    course.add_student(liker)
    comment.like(user=liker)
    assert req.reload().is_completed(liker)


def test_wont_count_like_self():
    comment = utils.comment.lazy_add_comment()
    course = Course(comment.problem.course)
    task = Task.add(course=course)
    req = requirement.LikeOthersComment.add(
        task=task,
        required_number=1,
    )
    comment.like(user=comment.author)
    assert not req.reload().is_completed(comment.author)
