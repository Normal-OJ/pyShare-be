import secrets
from mongo import *
from mongo import engine
from mongo.config import config
from tests import utils
from typing import Callable, Optional
from flask.testing import FlaskClient


def teardown_function(_):
    utils.mongo.drop_db()


def test_sandbox_init(forge_client: Callable[[str, Optional[str]],
                                             FlaskClient]):
    # Config initial sandbox
    url = 'http://test.sandbox'
    token = 'TestToken'
    config['sandbox'] = {
        'url': url,
        'token': token,
    }
    # Get sandbox & validate
    admin = utils.user.Factory.admin()
    client = forge_client(admin.username)
    rv = client.get('/sandbox')
    assert rv.status_code == 200
    rv_json = rv.get_json()
    assert len(rv_json['data']) == 1
    sandbox = rv_json['data'][0]
    assert sandbox['url'] == url
    assert 'token' not in sandbox
    # TODO: Remove key instead of setting it to None
    # teardown
    config['sandbox'] = None


def test_create_sandbox(forge_client: Callable[[str, Optional[str]],
                                               FlaskClient]):
    assert len(engine.Sandbox.objects) == 0
    admin = utils.user.Factory.admin()
    client = forge_client(admin.username)
    url = 'http://test.sandbox'
    token = 'TestToken'
    rv = client.post(
        '/sandbox',
        json={
            'url': url,
            'token': token,
        },
    )
    assert rv.status_code == 200
    sandbox = engine.Sandbox.objects(url=url).get()
    assert sandbox.token == token


def test_delete_sandbox(forge_client: Callable[[str, Optional[str]],
                                               FlaskClient]):
    url = 'http://test.sandbox'
    engine.Sandbox(
        url=url,
        token=secrets.token_urlsafe(),
    ).save(force_insert=True)
    assert engine.Sandbox.objects(url=url).get().url == url
    admin = utils.user.Factory.admin()
    client = forge_client(admin.username)
    client.delete('/sandbox', json={'url': url})
    assert len(engine.Sandbox.objects) == 0


def test_update_sandbox(forge_client: Callable[[str, Optional[str]],
                                               FlaskClient]):
    url = 'http://test.sandbox'
    engine.Sandbox(
        url=url,
        token=secrets.token_urlsafe(),
    ).save(force_insert=True)
    admin = utils.user.Factory.admin()
    client = forge_client(admin.username)
    rv = client.put(
        '/sandbox',
        json={
            'url': url,
            'alias': 'sandbox',
        },
    )
    assert rv.status_code == 200
    sandbox = engine.Sandbox.objects(url=url).get()
    assert sandbox.alias == 'sandbox'
