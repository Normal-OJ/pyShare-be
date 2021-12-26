from mongo import Task
from mongo import requirement
from mongo.sandbox import ISandbox
from tests import utils


def setup_function(_):
    ISandbox.use(utils.submission.MockSandbox)


def teardown_function(_):
    ISandbox.use(None)
    utils.mongo.drop_db()


def test_progress():
    course = utils.course.lazy_add()
    task = Task.add(course=course)
    user = utils.user.Factory.student()
    course.add_student(user)
    assert task.progress(user) == (0, 0)
    problem = utils.problem.lazy_add(
        course=course,
        is_oj=True,
    )
    req = requirement.SolveOJProblem.add(
        task=task,
        problems=[problem],
    )
    task.update(push__requirements=req.id)
    assert task.reload().progress(user) == (0, 1)
    submission = utils.submission.lazy_add_new(user=user, problem=problem)
    submission.complete(judge_result=submission.engine.JudgeResult.AC)
    assert task.reload().progress(user) == (1, 1)
