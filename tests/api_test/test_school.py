from mongo import *
from mongo import engine
from tests import utils
from typing import Callable, Optional
import pytest
from flask.testing import FlaskClient


def setup_function(_):
    utils.mongo.drop_db()


def test_admin_can_operate(forge_client: Callable[[str], FlaskClient]):
    u = utils.user.Factory.admin()
    client = forge_client(u.username)
    # There should be no school
    rv = client.get('/school')
    assert rv.status_code == 200, rv.get_json()
    # There should be only one school denotes "No school"
    assert len(rv.get_json()['data']) == 1


@pytest.mark.parametrize(
    'user',
    [
        utils.user.Factory.student,
        utils.user.Factory.teacher,
    ],
)
def test_other_role_can_not_operate(
    user: Callable[[], User],
    forge_client: Callable[[str], FlaskClient],
):
    client = forge_client(user().username)
    # Anyone can query
    rv = client.get('/school')
    assert rv.status_code == 200
    # But can not find nonexistent school
    rv = client.get('/school/anything')
    assert rv.status_code == 404
    # And can not create new school
    rv = client.post(
        '/school',
        json={
            'abbr': 'NTNU',
            'name': 'National Taiwan Normal University',
        },
    )
    assert rv.status_code == 403
    # No school was inserted to DB
    assert len(engine.School.objects) == 1


def test_add_school(forge_client: Callable[[str, Optional[str]], FlaskClient]):
    u = utils.user.Factory.admin()
    assert engine.User.objects.get(username=u.username)
    client = forge_client(u.username)
    # Try add a new school
    school_json = {
        'abbr': 'NTNU',
        'name': 'National Taiwan Normal University',
    }
    rv = client.post(
        '/school',
        json=school_json,
    )
    assert rv.status_code == 200, rv.get_json()
    # Check the school was inseted
    assert len(engine.School.objects) == 2
    assert engine.School.objects(abbr=school_json['abbr'])


def test_admin_get_one(forge_client: Callable[[str], FlaskClient]):
    u = utils.user.Factory.admin()
    client = forge_client(u.username, u.school)
    school = engine.School(
        abbr='NTNU',
        name='National Taiwan Normal University',
    ).save()
    rv = client.get(f'/school/{school.abbr}')
    assert rv.status_code == 200, rv.get_json()
    assert rv.get_json()['data'] == school.to_dict()
