import pytest
from mongo import *
from mongo import engine
from tests import utils


@pytest.mark.parametrize(
    'tags',
    [
        ['tag'],
        ['tag1', 'tag2'],
    ],
)
def test_course_check_tags(tags):
    c = utils.course.lazy_add(tags=tags)
    for tag in tags:
        assert c.check_tag(tag)


def test_course_update_tags():
    c = utils.course.lazy_add(tags=['tag1', 'tag2'])
    c.patch_tag(['tag3'], ['tag1'])
    assert c.tags == ['tag2', 'tag3']


def test_course_statistic():
    # It's function is broken
    # c = utils.course.lazy_add()
    # assert c.statistic_file()
    assert False


def test_course_permission():
    teacher = utils.user.lazy_signup(username='teacher', role=1)
    student = utils.user.lazy_signup(username='student')
    nobody = utils.user.lazy_signup(username='nobody')
    c = utils.course.lazy_add(teacher=teacher,
                              status=engine.Course.Status.READONLY)
    c.update(add_to_set__students=student.obj)
    c = c.reload()

    assert c.own_permission(user=teacher) == set([*'rpw'])
    assert c.own_permission(user=student) == set([*'rp'])
    assert c.own_permission(user=nobody) == set([*'r'])
