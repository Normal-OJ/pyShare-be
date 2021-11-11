from tests import utils
from mongo import User


def setup_function(_):
    utils.mongo.drop_db()


def test_problem_has_reference_count_in_user_statistic():
    src_problem = utils.problem.lazy_add()
    assert src_problem.reference_count == 0
    target_course = utils.course.lazy_add()
    src_problem.copy(
        target_course=target_course,
        is_template=False,
        user=target_course.teacher,
    )
    statistic = User(src_problem.author).statistic()
    assert len(statistic['problems']) == 1
    found_problem = statistic['problems'][0]
    assert found_problem['pid'] == src_problem.pid
    assert found_problem['referenceCount'] == 1
