import pytest
from mongo import *
from mongo import engine
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def random_teacher():
    # 1 is role id for teacher
    return utils.user.lazy_signup(role=1)


@pytest.mark.parametrize(
    'role',
    [
        0,
        1,
        pytest.param(
            2,
            marks=pytest.mark.xfail,
        ),
    ],
)
def test_user_permission(role):
    user = utils.user.lazy_signup()
    user.update(role=role)
    user = user.reload()
    utils.course.lazy_add(teacher=user)


@pytest.mark.parametrize(
    'status',
    [
        engine.CourseStatus.PRIVATE,
        engine.CourseStatus.PUBLIC,
        engine.CourseStatus.READONLY,
        pytest.param(
            -10086,
            marks=pytest.mark.xfail,
        ),
        pytest.param(
            55688,
            marks=pytest.mark.xfail,
        ),
    ],
)
def test_course_status(status):
    user = random_teacher()
    c = utils.course.lazy_add(teacher=user, status=status)
    assert c.status == status


@pytest.mark.parametrize(
    'name',
    [
        'Computer-Programming-I',
        'Data_Analysis',
        'Object.Oreiented.Analysis.and.Design',
        '資訊安全',
        'Algorithm in Daliy Lives',
    ],
)
def test_normal_course_name(name):
    user = random_teacher()
    c = utils.course.lazy_add(name=name, teacher=user)
    assert c.name == name


@pytest.mark.parametrize(
    'name, exception',
    [
        ('A' * 65, ValidationError),
        ('@A@', ValidationError),
        ('Computer/Programming/I', ValidationError),
        ('', ValidationError),
    ],
)
def test_invalid_course_name(name, exception):
    user = random_teacher()
    with pytest.raises(exception, match=r'.*name.*'):
        utils.course.lazy_add(name=name, teacher=user)
