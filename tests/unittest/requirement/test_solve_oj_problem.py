import pytest
from datetime import datetime, timedelta
from tests import utils
from mongo.sandbox import ISandbox
from mongo import requirement


def setup_function(_):
    ISandbox.use(utils.submission.MockSandbox)


def teardown_function(_):
    ISandbox.use(None)
    utils.mongo.drop_db()


# TODO: Simplify setup procedure


def test_can_count_AC_submission():
    problem = utils.problem.lazy_add(is_oj=True)
    task = utils.task.lazy_add(course=problem.course)
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
    assert req.reload().is_completed(submission.user)


def test_wont_be_triggerd_by_WA_submission():
    problem = utils.problem.lazy_add(is_oj=True)
    task = utils.task.lazy_add(
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
    task = utils.task.lazy_add(course=problem.course)
    with pytest.raises(ValueError, match=r'.*accept.*OJ problem.*'):
        requirement.SolveOJProblem.add(
            task=task,
            problems=[problem],
        )


def test_cannot_initialize_with_empty_problem_list():
    task = utils.task.lazy_add(course=utils.course.lazy_add())
    with pytest.raises(ValueError, match=r'.*empty.*'):
        requirement.SolveOJProblem.add(
            task=task,
            problems=[],
        )


def test_progress():
    problem = utils.problem.lazy_add(is_oj=True)
    task = utils.task.lazy_add(
        course=problem.course,
        ends_at=datetime.now() + timedelta(minutes=5),
    )
    req = requirement.SolveOJProblem.add(
        task=task,
        problems=[problem],
    )
    user = utils.user.Factory.student()
    assert req.progress(user) == (0, 1)
    submission = utils.submission.lazy_add_new(
        user=user,
        problem=problem,
    )
    submission.complete(judge_result=submission.JudgeResult.AC)
    assert req.reload().progress(user) == (1, 1)


def test_sync():
    problem = utils.problem.lazy_add(is_oj=True)
    submission = utils.submission.lazy_add_new(problem=problem)
    submission.complete(judge_result=submission.JudgeResult.AC)
    task = utils.task.lazy_add(course=problem.course)
    req = requirement.SolveOJProblem.add(
        task=task,
        problems=[problem],
    )
    user = submission.user
    assert req.progress(user) == (0, 1)
    req.sync(users=[user])
    assert req.reload().progress(user) == (1, 1)


def test_extend_task_due_can_update_requirement():
    # Create a task ends now
    now = datetime.now()
    problem = utils.problem.lazy_add(is_oj=True)
    task = utils.task.lazy_add(course=problem.course, ends_at=now)
    user = utils.course.student(course=task.course)
    req = requirement.SolveOJProblem.add(
        task=task,
        problems=[problem],
    )
    # Create a AC submission
    submission = utils.submission.lazy_add_new(user=user, problem=problem)
    submission.complete(judge_result=submission.JudgeResult.AC)
    assert req.progress(user) == (0, 1)
    task.edit(ends_at=now + timedelta(days=1))
    assert req.reload().progress(user) == (1, 1)
