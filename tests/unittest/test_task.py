from mongo import Course
from mongo import requirement
from mongo.sandbox import ISandbox
from tests import utils


def setup_function(_):
    ISandbox.use(utils.submission.MockSandbox)


def teardown_function(_):
    ISandbox.use(None)
    utils.mongo.drop_db()


def test_progress():
    task = utils.task.lazy_add()
    user = utils.user.Factory.student()
    course = Course(task.course)
    course.add_student(user)
    assert task.progress(user) == (0, 0)
    problem = utils.problem.lazy_add(
        course=course,
        is_oj=True,
    )
    # Reload to ensure that course data is up to date
    task.reload('course')
    requirement.SolveOJProblem.add(
        task=task,
        problems=[problem],
    )
    assert task.reload().progress(user) == (0, 1)
    submission = utils.submission.lazy_add_new(user=user, problem=problem)
    submission.complete(judge_result=submission.engine.JudgeResult.AC)
    assert task.reload().progress(user) == (1, 1)
