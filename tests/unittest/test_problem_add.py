import pytest
from tests import utils
import concurrent.futures


def setup_function(_):
    utils.mongo.drop_db()


def test_auto_increment_id():
    cnt = 10
    course = utils.course.lazy_add()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        p_futures = [
            executor.submit(utils.problem.lazy_add, course=course)
            for _ in range(cnt)
        ]
    pids = [p.result().pid for p in p_futures]
    assert sorted(pids) == [*range(1, cnt + 1)]


# TODO: define payload as enum in utils
@pytest.mark.parametrize(
    'user, course, valid',
    [
        (
            utils.user.Factory.admin,
            utils.course.Factory.default,
            True,
        ),
        (
            utils.user.Factory.teacher,
            utils.course.Factory.default,
            True,
        ),
        (
            utils.user.Factory.teacher,
            utils.course.Factory.private,
            False,
        ),
    ],
)
def test_problem_add_permission(user, course, valid):
    user = user()
    course = course()
    if valid:
        utils.problem.lazy_add(author=user, course=course)
    else:
        with pytest.raises(PermissionError):
            utils.problem.lazy_add(author=user, course=course)
