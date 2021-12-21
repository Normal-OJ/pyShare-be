import secrets
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def test_problem_copy():
    user = utils.user.Factory.teacher()
    user2 = utils.user.Factory.teacher()
    course1 = utils.course.Factory.default()
    course2 = utils.course.Factory.default()
    problem1 = utils.problem.lazy_add(author=user, course=course1)
    problem2 = problem1.copy(
        target_course=course2,
        is_template=False,
        user=user2,
    )

    dicts = [problem1.to_dict(), problem2.to_dict()]
    assert dicts[0]['author'] != dicts[1]['author']
    for d in dicts:
        del d['timestamp']
        del d['pid']
        del d['course']
        del d['comments']
        del d['author']

    assert dicts[0] == dicts[1]


def test_problem_copy_should_add_tag_to_target_course():
    tags = [secrets.token_hex(5) for _ in range(5)]
    course_src = utils.course.lazy_add(
        normal_problem_tags=tags,
        auto_insert_tags=True,
    )
    problem_src = utils.problem.lazy_add(
        course=course_src,
        tags=tags,
    )
    course_dst = utils.course.lazy_add()
    assert len(course_dst.tags) == 0
    problem_src.copy(
        target_course=course_dst,
        is_template=False,
        user=course_dst.teacher,
    )
    course_dst.reload('tags')
    assert sorted(course_dst.normal_problem_tags) == sorted(tags)


def test_problem_copy_should_add_reference_count():
    src_problem = utils.problem.lazy_add()
    for i in range(5):
        target_course = utils.course.lazy_add()
        src_problem.copy(
            target_course=target_course,
            is_template=False,
            user=target_course.teacher,
        )
        src_problem.reload('reference_count')
        assert src_problem.reference_count == i + 1
