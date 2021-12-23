from mongo.course import Course
from tests import utils
from mongo import User, ISandbox


def setup_function(_):
    utils.mongo.drop_db()
    ISandbox.use(utils.submission.MockSandbox)


def teardown_function(_):
    ISandbox.use(None)


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


def test_user_statistic_only_contains_normal_comments():
    normal = utils.problem.lazy_add(
        is_oj=False,
        allow_multiple_comments=True,
    )
    author = utils.user.Factory.student()
    Course(normal.course).add_student(author)
    for _ in range(7):
        utils.comment.lazy_add_comment(
            problem=utils.problem.lazy_add(
                is_oj=True,
                course=normal.course,
            ),
            author=author,
        )
    normal_cnt = 5
    normal_comments = [
        utils.comment.lazy_add_comment(
            author=author,
            problem=normal,
        ).id for _ in range(normal_cnt)
    ]
    stats = author.reload().statistic()
    for key in ('comments', 'execInfo'):
        value = stats[key]
        assert len(value) == normal_cnt
        for comment in value:
            assert comment['id'] in normal_comments


def test_user_statistic_liked_does_not_contain_comments_without_like_by_default(
):
    no_like = utils.comment.lazy_add_comment()
    author = User(no_like.author).reload()
    stats = author.statistic()
    assert len(stats['liked']) == 0
    stats = author.statistic(full=True)
    assert len(stats['liked']) == 1
