from typing import List
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
def test_course_check_tags(tags: List[str]):
    c = utils.course.lazy_add(
        tags=tags,
        auto_insert_tags=True,
    )
    for tag in tags:
        assert c.check_tag(tag)


def test_course_update_tags():
    tags = ['tag1', 'tag2', 'tag3']
    for tag in tags:
        Tag.add(tag)
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


def test_course_oj_statistic():
    # Setup course and student
    c = utils.course.lazy_add()
    student = utils.user.lazy_signup(username='student')
    c.add_student(student)
    # Create some oj problem
    cnt = 10
    ps = [
        utils.problem.lazy_add(
            course=c,
            author=c.teacher,
            is_oj=True,
        ) for _ in range(cnt)
    ]
    stat = c.oj_statistic(ps)
    problem_overview = {
        'acCount': 0,
        'tryCount': 0,
        'acUser': 0,
        'tryUser': 0,
    }
    for p in ps:
        assert stat['overview'][str(p.pid)] == problem_overview
    user_stats = stat['users']
    assert len(user_stats) == 1
    user_stat = user_stats[0]
    assert user_stat['info']['username'] == student.username
    assert user_stat['overview'] == {
        'acCount': 0,
        'tryCount': 0,
    }
    problem_stat = {
        'commentId': None,
        'result': User.OJProblemResult.NO_TRY,
        'tryCount': 0,
    }
    for p in ps:
        assert user_stat[str(p.pid)] == problem_stat


def test_course_permission():
    nobody = utils.user.lazy_signup(username='nobody')
    c = utils.course.lazy_add(status=engine.Course.Status.READONLY)
    student = utils.course.student(c)
    assert c.own_permission(user=c.teacher) == {*'rpw'}
    assert c.own_permission(user=student) == {*'rp'}
    assert c.own_permission(user=nobody) == {*'r'}
