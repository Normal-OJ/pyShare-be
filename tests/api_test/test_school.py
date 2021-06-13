from mongo import engine
from tests import utils
from typing import Callable
from flask.testing import FlaskClient


def setup_function(_):
    utils.mongo.drop_db()


def test_admin_can_operate(forge_client: Callable[[str], FlaskClient]):
    u = utils.user.Factory.admin()
    client = forge_client(u.username)
    # There should be no school
    rv = client.get('/school')
    assert rv.status_code == 200, rv.get_json()
    assert len(rv.get_json()['data']) == 0


@pytest.mark.parametrize(
    'user',
    [
        utils.user.Factory.student(),
        utils.user.Factory.teacher(),
    ],
)
def test_other_role_can_not_operate(
    user: User,
    forge_client: Callable[[str], FlaskClient],
):
    client = forge_client(user.username)
    rv = client.get('/school')
    assert rv.status_code == 403
    rv = client.get('/school/anything')
    assert rv.status_code == 403
    rv = client.post('/school')
    assert rv.status_code == 403


def test_add_school(forge_client: Callable[[str], FlaskClient]):
    u = utils.user.Factory.admin()
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
    schools = rv.get_json()['data']
    assert len(schools) == 1
    assert schools[0] == school_json


def test_admin_get_one(forge_client: Callable[[str], FlaskClient]):
    u = utils.user.Factory.admin()
    client = forge_client(u.username)
    school = engine.School(
        abbr='NTNU',
        name='National Taiwan Normal University',
    ).save()
    rv = client.delete(f'/school/{school.abbr}')
    assert rv.status_code == 200, rv.get_json()
    assert rv.get_json()['data'] == school.to_dict()
