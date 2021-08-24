import secrets
from typing import Callable
from flask.testing import FlaskClient
from mongo import Tag
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def random_tag_str():
    return secrets.token_hex(8)


def test_add_tag(forge_client: Callable[[str], FlaskClient]):
    assert len(Tag.engine.objects) == 0
    tag_str = random_tag_str()
    teacher = utils.user.Factory.teacher()
    client = forge_client(teacher.username)
    rv = client.post(
        '/tag',
        json={'tags': [tag_str]},
    )
    assert rv.status_code == 200, rv.get_json()
    assert len(Tag.engine.objects) == 1
    assert Tag(tag_str)
