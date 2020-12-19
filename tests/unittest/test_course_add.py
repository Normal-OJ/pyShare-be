import pytest
from mongo import *
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def random_teacher():
    user = utils.user.randomly_add()
    # change its role to teacher
    user.update(role=1)
    return user.reload()


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
    data = utils.course.data(name=name, teacher=user)
    Course.add(**data)


@pytest.mark.parametrize(
    'name, exception',
    [
        ('A' * 65, ValidationError),
        ('@A@', ValueError),
        ('Computer/Programming/I', ValueError),
        ('', ValueError),
    ],
)
def test_invalid_course_name(name, exception):
    user = random_teacher()
    with pytest.raises(exception, match=r'.*name.*'):
        data = utils.course.data(name=name, teacher=user)
        Course.add(**data)
