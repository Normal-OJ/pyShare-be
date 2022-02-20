from typing import Callable
from flask.testing import FlaskClient
from mongo import Course, Task, requirement
from tests import utils
from datetime import datetime, timedelta


def setup_function(_):
    utils.mongo.drop_db()


def test_add_task(forge_client: Callable[[str], FlaskClient], config_app):
    config_app(env='test')
    client = forge_client('teacher1')
    cid = Course.get_by_name('course_108-1').pk
    rv = client.post(
        '/task',
        json={
            'course': cid,
            'title': 'My task',
        },
    )
    assert rv.status_code == 200, rv.get_json()
    tid = rv.get_json()['data']['id']
    assert Task(tid).course.id == cid

    rv = client.get(f'/task/{tid}')
    assert rv.status_code == 200, rv.get_json()
    for key in ('id', 'endsAt', 'startsAt'):
        assert key in rv.get_json()['data']
    # The timestamps should be ISO string
    for key in ('endsAt', 'startsAt'):
        assert isinstance(rv.get_json()['data'][key], str)


def test_edit_task(forge_client: Callable[[str], FlaskClient]):
    now = datetime.now()
    reply = utils.comment.lazy_add_reply()
    course = Course(reply.problem.course)
    task = utils.task.lazy_add(
        course=course,
        starts_at=now - timedelta(days=1),
        ends_at=now,
    )
    user = reply.author
    client = forge_client(task.course.teacher.username)

    utils.comment.lazy_add_reply()
    req = requirement.ReplyToComment.add(
        task=task,
        required_number=1,
    )
    assert req.progress(user) == (0, 1)

    data = {
        'title': 'My task',
        'content': 'haha',
        'startsAt': (now - timedelta(days=2)).isoformat(),
        'endsAt': (now + timedelta(days=1)).isoformat(),
    }
    rv = client.put(
        f'/task/{task.id}',
        json=data,
    )
    assert rv.status_code == 200, rv.get_json()
    rv = client.get(f'/task/{task.id}')
    assert rv.status_code == 200, rv.get_json()
    for key in ('title', 'content'):
        assert data[key] == rv.get_json()['data'][key]
    assert req.reload().progress(user) == (1, 1)


def test_edit_task_with_shrink_time(forge_client: Callable[[str],
                                                           FlaskClient]):
    now = datetime.now()
    reply = utils.comment.lazy_add_reply()
    course = Course(reply.problem.course)
    task = utils.task.lazy_add(
        course=course,
        starts_at=now - timedelta(days=3),
        ends_at=now + timedelta(days=1),
    )
    user = reply.author
    client = forge_client(task.course.teacher.username)

    utils.comment.lazy_add_reply()
    req = requirement.ReplyToComment.add(
        task=task,
        required_number=1,
    )
    req.sync()
    assert req.reload().progress(user) == (1, 1)

    data = {
        'title': 'My task',
        'content': 'haha',
        'startsAt': (now - timedelta(days=2)).isoformat(),
        'endsAt': (now - timedelta(days=1)).isoformat(),
    }
    rv = client.put(
        f'/task/{task.id}',
        json=data,
    )
    assert rv.status_code == 200, rv.get_json()
    rv = client.get(f'/task/{task.id}')
    assert rv.status_code == 200, rv.get_json()
    for key in ('title', 'content'):
        assert data[key] == rv.get_json()['data'][key]
    assert req.reload().progress(user) == (0, 1)


def test_delete_task(forge_client: Callable[[str], FlaskClient]):
    reply = utils.comment.lazy_add_reply()
    course = Course(reply.problem.course)
    task = utils.task.lazy_add(course=course)
    client = forge_client(task.course.teacher.username)
    req = requirement.ReplyToComment.add(
        task=task,
        required_number=1,
    )

    rv = client.delete(f'/task/{task.id}')
    assert rv.status_code == 200, rv.get_json()
    rv = client.get(f'/task/{task.id}')
    assert rv.status_code == 404, rv.get_json()
    rv = client.get(f'/requirement/{req.id}')
    assert rv.status_code == 404, rv.get_json()


def test_like_others_comment_requirement(
    forge_client: Callable[[str], FlaskClient],
    config_app,
):
    config_app(env='test')
    client = forge_client('teacher1')
    cid = Course.get_by_name('course_108-1').pk
    tid = str(utils.task.lazy_add(course=cid).id)
    rv = client.post(
        f'/task/{tid}/like-others-comment',
        json={'requiredNumber': 3},
    )
    assert rv.status_code == 200, rv.get_json()

    rv = client.get(f'/task/{tid}')
    rid = rv.get_json()['data']['requirements'][0]
    assert rv.status_code == 200, rv.get_json()
    assert rv.get_json()['data']['course'] == str(cid)

    rv = client.get(f'/requirement/{rid}')
    assert rv.status_code == 200, rv.get_json()
    assert rv.get_json()['data']['task'] == str(tid)


def test_solve_oj_problem_requirement(
    forge_client: Callable[[str], FlaskClient],
    config_app,
):
    config_app(env='test')
    client = forge_client('teacher1')
    course = Course.get_by_name('course_108-1')
    cid = course.pk
    tid = str(utils.task.lazy_add(course=cid).id)
    pid = int(
        utils.problem.lazy_add(
            course=course,
            allow_multiple_comments=True,
            is_oj=True,
        ).id)
    rv = client.post(
        f'/task/{tid}/solve-oj-problem',
        json={'problems': [pid]},
    )
    assert rv.status_code == 200, rv.get_json()

    rv = client.get(f'/task/{tid}')
    rid = rv.get_json()['data']['requirements'][0]
    assert rv.status_code == 200, rv.get_json()
    assert rv.get_json()['data']['course'] == str(cid)

    rv = client.get(f'/requirement/{rid}')
    assert rv.status_code == 200, rv.get_json()
    assert rv.get_json()['data']['task'] == str(tid)


def test_leave_comment_requirement(
    forge_client: Callable[[str], FlaskClient],
    config_app,
):
    config_app(env='test')
    client = forge_client('teacher1')
    course = Course.get_by_name('course_108-1')
    cid = course.pk
    tid = str(utils.task.lazy_add(course=cid).id)
    pid = int(
        utils.problem.lazy_add(
            course=course,
            allow_multiple_comments=True,
        ).id)
    rv = client.post(
        f'/task/{tid}/leave-comment',
        json={'problem': pid},
    )
    assert rv.status_code == 200, rv.get_json()

    rv = client.get(f'/task/{tid}')
    rid = rv.get_json()['data']['requirements'][0]
    assert rv.status_code == 200, rv.get_json()
    assert rv.get_json()['data']['course'] == str(cid)

    rv = client.get(f'/requirement/{rid}')
    assert rv.status_code == 200, rv.get_json()
    assert rv.get_json()['data']['task'] == str(tid)


def test_reply_to_comment_requirement(
    forge_client: Callable[[str], FlaskClient],
    config_app,
):
    config_app(env='test')
    client = forge_client('teacher1')
    cid = Course.get_by_name('course_108-1').pk
    tid = str(utils.task.lazy_add(course=cid).id)
    rv = client.post(
        f'/task/{tid}/reply-to-comment',
        json={'requiredNumber': 3},
    )
    assert rv.status_code == 200, rv.get_json()

    rv = client.get(f'/task/{tid}')
    rid = rv.get_json()['data']['requirements'][0]
    assert rv.status_code == 200, rv.get_json()
    assert rv.get_json()['data']['course'] == str(cid)

    rv = client.get(f'/requirement/{rid}')
    assert rv.status_code == 200, rv.get_json()
    assert rv.get_json()['data']['task'] == str(tid)


def test_get_course_task(
    forge_client: Callable[[str], FlaskClient],
    config_app,
):
    config_app(env='test')
    client = forge_client('teacher1')
    cid = Course.get_by_name('course_108-1').pk
    tid = str(utils.task.lazy_add(course=cid).id)
    rv = client.get(f'/course/{cid}/tasks')
    assert rv.status_code == 200, rv.get_json()
    assert tid in rv.get_json()['data']


def test_delete_requirement(forge_client: Callable[[str], FlaskClient]):
    reply = utils.comment.lazy_add_reply()
    course = Course(reply.problem.course)
    task = utils.task.lazy_add(course=course)
    client = forge_client(task.course.teacher.username)
    req = requirement.ReplyToComment.add(
        task=task,
        required_number=1,
    )
    rv = client.get(f'/requirement/{req.id}')
    assert rv.status_code == 200, rv.get_json()

    rv = client.delete(f'/requirement/{req.id}')
    assert rv.status_code == 200, rv.get_json()
    rv = client.get(f'/requirement/{req.id}')
    assert rv.status_code == 404, rv.get_json()
    rv = client.get(f'/task/{task.id}')
    assert rv.status_code == 200, rv.get_json()
    assert str(req.id) not in rv.get_json()['data']['requirements']
