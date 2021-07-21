from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def test_problem_copy():
    user = utils.user.Factory.teacher()
    course1 = utils.course.Factory.default()
    course2 = utils.course.Factory.default()
    problem1 = utils.problem.lazy_add(author=user, course=course1)
    problem2 = problem1.copy(target_course=course2, is_template=False)

    dicts = [problem1.to_dict(), problem2.to_dict()]
    for i in range(2):
        del dicts[i]['timestamp']
        del dicts[i]['pid']
        del dicts[i]['course']
        del dicts[i]['comments']

    assert dicts[0] == dicts[1]
    
