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
    problem = utils.problem.lazy_add(is_oj=True)
    task = Task.add(course=problem.course)
    with pytest.raises(ValueError, match=r'.*problem.*'):
        requirement.LeaveComment.add(
            task=task,
            problem=problem,
        )


def test_can_count_comment():
    problem = utils.problem.lazy_add(is_oj=False)
    task = Task.add(course=problem.course)
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
