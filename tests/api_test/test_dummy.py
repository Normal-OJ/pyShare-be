import secrets
from typing import Callable
from flask.testing import FlaskClient
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
    def setup_class(cls):
        cls.admin = utils.user.Factory.admin()

    @classmethod
    def teardown_class(cls):
        utils.mongo.drop_db()
        cls.admin = None

    def test_user_creation(self, forge_client: Callable[[str], FlaskClient]):
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
