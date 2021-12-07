import pytest
from datetime import datetime, timedelta
from tests import utils
from mongo.sandbox import ISandbox
from mongo.task import Task
from mongo import requirement


def setup_function(_):
    ISandbox.use(utils.submission.MockSandbox)


def teardown_function(_):
    ISandbox.use(None)
    utils.mongo.drop_db()


# TODO: Simplify setup procedure


def test_can_count_AC_submission():
    problem = utils.problem.lazy_add(is_oj=True)
    task = Task.add(course=problem.course)
    req = requirement.SolveOJProblem.add(
        task=task,
        problems=[problem],
    )
    submission = utils.submission.lazy_add_new(problem=problem)
    submission.complete(
        files=[],
        stdout='',
        stderr='',
        judge_result=submission.JudgeResult.AC,
    )
    print(
        submission.user.id,
        req.reload().get_record(submission.user).completes,
    )
    assert req.reload().is_completed(submission.user)


def test_wont_be_triggerd_by_WA_submission():
    problem = utils.problem.lazy_add(is_oj=True)
    task = Task.add(
        course=problem.course,
        ends_at=datetime.now() + timedelta(minutes=5),
    )
    req = requirement.SolveOJProblem.add(
        task=task,
        problems=[problem],
    )
    submission = utils.submission.lazy_add_new(problem=problem)
    submission.complete(
        files=[],
        stdout='',
        stderr='',
        judge_result=submission.JudgeResult.WA,
    )
    assert not req.reload().is_completed(submission.user)


def test_wont_accept_normal_problem():
    problem = utils.problem.lazy_add()
    task = Task.add(course=problem.course)
    with pytest.raises(ValueError, match=r'.*accept.*OJ problem.*'):
        requirement.SolveOJProblem.add(
            task=task,
            problems=[problem],
        )
