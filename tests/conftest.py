from typing import Optional
from app import setup_app
from mongo import *
from mongo import engine
import pytest
from tests import utils


@pytest.fixture(scope='function')
def config_app():
    def config_app(config=None, env=None):
        return setup_app(config, env)

    ISandbox.use(utils.submission.MockSandbox)
    yield config_app
    # clean db
    utils.mongo.drop_db()
    ISandbox.use(None)


@pytest.fixture
def config_client(config_app):
    def config_client(config=None, env=None):
        return config_app(config, env).test_client()

    return config_client


@pytest.fixture
def client(config_client):
    '''
    Leave here for backward compatibility.
    '''
    return config_client()


@pytest.fixture
def forge_client(config_client):
    def cookied(
        username: str,
        school: str = '',
        env: Optional[str] = None,
    ):
        user = User.get_by_username(
            username=username,
            school=school,
        )
        client = config_client(env=env)
        client.set_cookie('test.test', 'piann', user.secret)
        return client

    return cookied


@pytest.fixture
def client_admin(forge_client):
    return forge_client('admin')


@pytest.fixture
def client_teacher(forge_client):
    return forge_client('teacher')


@pytest.fixture
def client_student(forge_client):
    return forge_client('student')


@pytest.fixture
def test_token():
    # Token for user: test
    return User('test').secret


@pytest.fixture
def test2_token():
    # Token for user: test2
    return User('test2').secret
