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
    c = utils.course.lazy_add()
    tester = utils.user.lazy_signup(username='tester')
    c.add_student(tester)
    c = c.reload()

    assert c.statistic_file().readlines() == [
        'username,problems,likes,comments,replies,liked,success,fail\n',
        'tester,0,0,0,0,0,0,0\n',
    ]


def test_course_permission():
    teacher = utils.user.lazy_signup(username='teacher',
                                     role=engine.User.Role.TEACHER)
    student = utils.user.lazy_signup(username='student')
    nobody = utils.user.lazy_signup(username='nobody')
    c = utils.course.lazy_add(teacher=teacher,
                              status=engine.Course.Status.READONLY)
    c.add_student(student)
    c = c.reload()

    assert c.own_permission(user=teacher) == {*'rpw'}
    assert c.own_permission(user=student) == {*'rp'}
    assert c.own_permission(user=nobody) == {*'r'}
