from typing import Callable
from flask.testing import FlaskClient
from tests import utils


def test_get_all_user(forge_client: Callable[[str], FlaskClient]):
    count = 10
    # Add some users
    for _ in range(count):
        u = utils.user.Factory.student()
    client = forge_client(u.username)
    rv = client.get('/user')
    rv_json = rv.json
    assert rv.status_code == 200, rv_json
    assert len(rv_json['data']) == count
