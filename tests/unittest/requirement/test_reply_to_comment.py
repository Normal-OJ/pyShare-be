from datetime import datetime, timedelta
import pytest
from tests import utils
from mongo import (
    requirement,
    Course,
    ISandbox,
)


def setup_function(_):
    ISandbox.use(utils.submission.MockSandbox)


def teardown_function(_):
    ISandbox.use(None)
    utils.mongo.drop_db()


@pytest.mark.parametrize('required_number', (1, 3))
def test_can_count_reply(required_number: int):
    problem = utils.problem.lazy_add()
    task = utils.task.lazy_add(course=problem.course)
    req = requirement.ReplyToComment.add(
        task=task,
        required_number=required_number,
    )
    user = utils.user.Factory.student()
    Course(problem.course).add_student(user)
    comment = utils.comment.lazy_add_comment(
        problem=problem,
        author=user,
    )
    for _ in range(required_number):
        assert not req.reload().is_completed(user)
        utils.comment.lazy_add_reply(
            comment=comment,
            author=user,
        )
    assert req.reload().is_completed(user)


def test_progress():
    problem = utils.problem.lazy_add()
    task = utils.task.lazy_add(course=problem.course)
    req = requirement.ReplyToComment.add(
        task=task,
        required_number=1,
    )
    user = utils.user.Factory.student()
    Course(problem.course).add_student(user)
    assert req.progress(user) == (0, 1)
    comment = utils.comment.lazy_add_comment(
        problem=problem,
        author=user,
    )
    utils.comment.lazy_add_reply(
        author=user,
        comment=comment,
    )
    assert req.reload().progress(user) == (1, 1)


def test_sync():
    reply = utils.comment.lazy_add_reply()
    course = Course(reply.problem.course)
    task = utils.task.lazy_add(course=course)
    req = requirement.ReplyToComment.add(
        task=task,
        required_number=1,
    )
    user = reply.author
    assert req.progress(user) == (0, 1)
    req.sync(users=[user])
    assert req.reload().progress(user) == (1, 1)


def test_extend_task_due_can_update_requirement():
    now = datetime.now()
    reply = utils.comment.lazy_add_reply()
    course = Course(reply.problem.course)
    task = utils.task.lazy_add(course=course, ends_at=now)
    req = requirement.ReplyToComment.add(
        task=task,
        required_number=1,
    )
    user = reply.author
    assert req.progress(user) == (0, 1)
    task.update(ends_at=now + timedelta(days=1))
    assert req.reload().progress(user) == (1, 1)
