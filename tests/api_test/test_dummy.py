import pytest
from flask.testing import FlaskClient
import secrets
from typing import Callable
from mongo import *
from tests import utils
from mongo.config import config


class TestFakeProdEnv:
    @classmethod
    def setup_class(cls):
        config.DEBUG = False

    @classmethod
    def teardown_class(cls):
        config.DEBUG = True

    def test_no_dummy_api_under_prod_config(self, config_client):
        client = config_client()
        assert client.application.config['DEBUG'] == False
        rv = client.get('/dummy')
        assert rv.status_code == 404


class TestCreateDummyResource:
    admin = None

    @classmethod
    def setup_method(cls, _):
        cls.admin = utils.user.Factory.admin()

    @classmethod
    def teardown_method(cls, _):
        cls.admin = None
        utils.mongo.drop_db()

    def test_create_user(
        self,
        forge_client: Callable[[str], FlaskClient],
    ):
        client = forge_client(self.admin.username)
        username = utils.user.random_username()
        password = secrets.token_hex()
        email = f'{username}@pyshare.io'
        rv = client.post(
            '/dummy/user',
            json={
                'username': username,
                'password': password,
                'email': email,
            },
        )
        assert rv.status_code == 200, rv.get_json()
        rv_json = rv.get_json()
        rv_user = rv_json['data']
        assert rv_user['username'] == username
        assert rv_user['email'] == email

    def test_create_comment(
        self,
        forge_client: Callable[[str], FlaskClient],
    ):
        client = forge_client(self.admin.username)
        title = secrets.token_hex()
        content = secrets.token_hex()
        rv = client.post(
            '/dummy/comment',
            json={
                'title': title,
                'content': content,
            },
        )
        assert rv.status_code == 200, rv.get_json()
        rv_comment = rv.get_json()['data']
        assert rv_comment['title'] == title
        assert rv_comment['content'] == content

    @pytest.mark.parametrize(
        ('res', 'val'),
        [
            ('author', '0' * 24),
            ('problem', 13),
        ],
    )
    def test_create_comment_with_non_existent_resource_should_fail(
        self,
        forge_client: Callable[[str], FlaskClient],
        res: str,
        val,
    ):
        client = forge_client(self.admin.username)
        with pytest.raises(DoesNotExist):
            client.post(
                '/dummy/comment',
                json={res: val},
            )
