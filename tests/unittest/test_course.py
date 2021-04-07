import pytest
from mongo import *
from mongo import engine
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


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
    student = utils.user.lazy_signup(username='student')
    c.add_student(student)
    c = c.reload()

    assert c.statistic_file().readlines() == [
        'username,problems,likes,comments,replies,liked,success,fail\n',
        'student,0,0,0,0,0,0,0\n',
    ]


def test_course_permission():
    nobody = utils.user.lazy_signup(username='nobody')
    c = utils.course.lazy_add(status=engine.Course.Status.READONLY)
    student = utils.course.student(c)
    assert c.own_permission(user=c.teacher) == {*'rpw'}
    assert c.own_permission(user=student) == {*'rp'}
    assert c.own_permission(user=nobody) == {*'r'}
