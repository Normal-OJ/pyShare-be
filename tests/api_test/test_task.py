from typing import Callable
from flask.testing import FlaskClient
from mongo import *
from mongo import engine
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def test_add_task(forge_client: Callable[[str], FlaskClient], config_app):
    config_app(env='test')
    client = forge_client('teacher1')
    cid = Course.get_by_name('course_108-1').pk
    rv = client.post(
        '/task',
        json={'course': cid},
    )
    assert rv.status_code == 200, rv.get_json()
    tid = rv.get_json()['data']['id']
    assert engine.Task.objects(id=tid)[0].course.id == cid


def test_get_task_and_requirement(forge_client: Callable[[str], FlaskClient],
                                  config_app):
    config_app(env='test')
    client = forge_client('teacher1')
    cid = Course.get_by_name('course_108-1').pk
    rv = client.post(
        '/task',
        json={'course': cid},
    )
    assert rv.status_code == 200, rv.get_json()
    tid = rv.get_json()['data']['id']

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


def test_get_course_task(forge_client: Callable[[str], FlaskClient],
                         config_app):
    config_app(env='test')
    client = forge_client('teacher1')
    cid = Course.get_by_name('course_108-1').pk
    rv = client.post(
        '/task',
        json={'course': cid},
    )
    assert rv.status_code == 200, rv.get_json()
    tid = rv.get_json()['data']['id']

    rv = client.get(f'/course/{cid}/tasks')
    assert rv.status_code == 200, rv.get_json()
    assert tid in rv.get_json()['data']