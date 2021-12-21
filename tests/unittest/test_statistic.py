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


def test_user_statistic_does_not_contain_oj_comments():
    p = utils.problem.lazy_add(is_oj=True)
    c = utils.comment.lazy_add_comment(problem=p)
    author = c.author
    cnt = 5
    cs = [utils.comment.lazy_add_comment(author=author) for _ in range(cnt)]
    stats = User(author).reload().statistic()
    assert len(author.comments) == cnt + 1
    assert len(stats['comments']) == cnt
    excepted = sorted(cs, key=lambda c: (c.problem.pid, c.floor))
    result = sorted(stats['comments'], key=lambda c: (c['pid'], c['floor']))
    for a, b in zip(excepted, result):
        assert a.problem.pid == b['pid']
        assert a.floor == b['floor']


def test_user_statistic_liked_does_not_contain_comments_without_like_by_default(
):
    no_like = utils.comment.lazy_add_comment()
    author = User(no_like.author).reload()
    stats = author.statistic()
    assert len(stats['liked']) == 0
    stats = author.statistic(full=True)
    assert len(stats['liked']) == 1
