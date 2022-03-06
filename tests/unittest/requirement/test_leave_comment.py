from datetime import datetime, timedelta
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


def test_cannot_initialize_with_oj_problem():
    task = utils.task.lazy_add()
    problem = utils.problem.lazy_add(is_oj=True, course=task.course)
    task.reload('course')
    with pytest.raises(ValueError, match=r'.*problem.*'):
        requirement.LeaveComment.add(
            task=task,
            problem=problem,
        )


def test_can_count_comment():
    task = utils.task.lazy_add()
    problem = utils.problem.lazy_add(is_oj=False, course=task.course)
    task.reload('course')
    req = requirement.LeaveComment.add(
        task=task,
        problem=problem,
    )
    user = utils.user.Factory.student()
    Course(problem.course).add_student(user)
    assert not req.is_completed(user)
    # Add unrelated comment won't affect task
    utils.comment.lazy_add_comment()
    assert not req.reload().is_completed(user)
    # And reply, neither
    utils.comment.lazy_add_reply()
    assert not req.reload().is_completed(user)
    utils.comment.lazy_add_comment(
        problem=problem,
        author=user,
    )
    assert req.reload().is_completed(user)


def test_progress():
    task = utils.task.lazy_add()
    problem = utils.problem.lazy_add(is_oj=False, course=task.course)
    task.reload('course')
    req = requirement.LeaveComment.add(
        task=task,
        problem=problem,
    )
    user = utils.user.Factory.student()
    Course(problem.course).add_student(user)
    assert req.progress(user) == (0, 1)
    utils.comment.lazy_add_comment(
        problem=problem,
        author=user,
    )
    assert req.reload().progress(user) == (1, 1)


def test_sync():
    comment = utils.comment.lazy_add_comment()
    task = utils.task.lazy_add(course=comment.problem.course)
    req = requirement.LeaveComment.add(
        task=task,
        problem=comment.problem,
    )
    user = comment.author
    assert req.progress(user) == (0, 1)
    req.sync(users=[user])
    assert req.reload().progress(user) == (1, 1)


def test_extend_task_due_can_update_requirement():
    now = datetime.now()
    comment = utils.comment.lazy_add_comment()
    task = utils.task.lazy_add(
        course=comment.problem.course,
        ends_at=now,
    )
    req = requirement.LeaveComment.add(
        task=task,
        problem=comment.problem,
    )
    user = comment.author
    assert req.progress(user) == (0, 1)
    task.edit(ends_at=now + timedelta(days=1))
    assert req.reload().progress(user) == (1, 1)
