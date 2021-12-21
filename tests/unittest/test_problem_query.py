import secrets
import random
from tests import utils
from mongo import (Problem, Tag, engine)


def setup_function(_):
    utils.mongo.drop_db()


def test_problem_filter():
    cnt = 10
    for _ in range(cnt):
        utils.problem.lazy_add()
    assert len(Problem.filter()) == cnt


def test_problem_filter_with_course():
    cnt = 10
    for _ in range(cnt):
        utils.problem.lazy_add()
    course = utils.course.lazy_add()
    expected_pids = [
        utils.problem.lazy_add(course=course).pid for _ in range(cnt)
    ]
    result_pids = [p.pid for p in Problem.filter(course=course.pk)]
    assert sorted(result_pids) == sorted(expected_pids)


def test_problem_filter_with_tag():
    cnt = 10
    random_tag = [secrets.token_hex(4) for _ in range(5)]
    for t in random_tag:
        Tag.add(t, engine.Tag.Category.NORMAL_PROBLEM)
    for _ in range(cnt):
        selected_tags = random.sample(random_tag, 2)
        course = utils.course.lazy_add(
            normal_problem_tags=selected_tags,
            auto_insert_tags=True,
        )
        utils.problem.lazy_add(
            tags=selected_tags,
            course=course,
        )
    target_tag = [secrets.token_hex(6) for _ in range(3)]
    course = utils.course.lazy_add(
        normal_problem_tags=target_tag,
        auto_insert_tags=True,
    )
    for _ in range(cnt):
        utils.problem.lazy_add(
            tags=target_tag,
            course=course,
        )
    assert len(Problem.filter(tags=target_tag)) == cnt


def test_problem_filter_normal_problem():
    cnt = 7
    excepted_pids = [utils.problem.lazy_add().pid for _ in range(cnt)]
    non_target_cnt = 13
    for _ in range(non_target_cnt):
        utils.problem.lazy_add(is_oj=True)
    result_pids = [p.pid for p in Problem.filter(type='NormalProblem')]
    assert sorted(excepted_pids) == sorted(result_pids)


def test_problem_filter_oj_problem():
    cnt = 7
    excepted_pids = [
        utils.problem.lazy_add(is_oj=True).pid for _ in range(cnt)
    ]
    non_target_cnt = 13
    for _ in range(non_target_cnt):
        utils.problem.lazy_add()
    result_pids = [p.pid for p in Problem.filter(type='OJProblem')]
    assert sorted(excepted_pids) == sorted(result_pids)
