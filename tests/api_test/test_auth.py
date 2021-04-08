import io
import csv
import secrets
from typing import Callable
from tests.utils.utils import partial_dict
import pytest
from tests import utils
from mongo import *
from flask.testing import FlaskClient
import jwt


def setup_function(_):
    utils.mongo.drop_db()


@pytest.mark.skip(reason='Directly signup is currently not supported.')
class TestSignup:
    '''Test Signup
    '''
    def test_without_username_and_email(self, client):
        # Signup without username and password
        rv = client.post('/auth/signup', json={'password': 'test'})
        json = rv.get_json()
        assert rv.status_code == 400
        assert json['status'] == 'err'
        assert json['message'] == 'Requested Value With Wrong Type'

    def test_empty_password(self, client):
        # Signup with empty password
        rv = client.post(
            '/auth/signup',
            json={
                'username': 'test',
                'email': 'test@test.test',
            },
        )
        json = rv.get_json()
        assert rv.status_code == 400
        assert json['status'] == 'err'
        assert json['message'] == 'Requested Value With Wrong Type'

    def test_signup(self, client):
        # Signup
        rv = client.post(
            '/auth/signup',
            json={
                'username': 'test',
                'password': 'test',
                'email': 'test@test.test',
            },
        )
        json = rv.get_json()
        assert rv.status_code == 200, json
        assert json['status'] == 'ok'
        assert json['message'] == 'Signup Success'
        # Signup a second user
        client.post(
            '/auth/signup',
            json={
                'username': 'test2',
                'password': 'test2',
                'email': 'test2@test.test'
            },
        )

    def test_used_username(self, client):
        # Signup with used username
        rv = client.post('/auth/signup',
                         json={
                             'username': 'test',
                             'password': 'test',
                             'email': 'test@test.test'
                         })
        json = rv.get_json()
        assert rv.status_code == 400
        assert json['status'] == 'err'
        assert json['message'] == 'User Exists'

    def test_used_email(self, client):
        # Signup with used email
        rv = client.post('/auth/signup',
                         json={
                             'username': 'test3',
                             'password': 'test',
                             'email': 'test@test.test'
                         })
        json = rv.get_json()
        assert rv.status_code == 400
        assert json['status'] == 'err'
        assert json['message'] == 'User Exists'


@pytest.mark.skip(reason='Active API is currently not supported.')
class TestActive:
    '''Test Active
    '''
    def test_redirect_with_invalid_toke(self, client):
        # Access active-page with invalid token
        rv = client.get('/auth/active/invalid_token')
        json = rv.get_json()
        assert rv.status_code == 403
        assert json['status'] == 'err'
        assert json['message'] == 'Invalid Token'

    def test_redirect(self, client, test_token):
        # Redirect to active-page
        rv = client.get(f'/auth/active/{test_token}')
        json = rv.get_json()
        assert rv.status_code == 302

    def test_update_with_invalid_data(self, client):
        # Update with invalid data
        rv = client.post(
            f'/auth/active',
            json={
                'profile': 123,  # profile should be a dictionary
            },
        )
        json = rv.get_json()
        assert rv.status_code == 400
        assert json['status'] == 'err'
        assert json['message'] == 'Requested Value With Wrong Type'

    def test_update_without_agreement(self, client):
        # Update without agreement
        rv = client.post(
            f'/auth/active',
            json={
                'profile': {},
                'agreement': 123
            },
        )
        json = rv.get_json()
        assert rv.status_code == 400
        assert json['status'] == 'err'
        assert json['message'] == 'Requested Value With Wrong Type'

    def test_update(self, client, test_token):
        # Update
        client.set_cookie('test.test', 'piann', test_token)
        rv = client.post(
            f'/auth/active',
            json={
                'displayName': 'Test',
                'agreement': True,
            },
        )
        json = rv.get_json()
        assert rv.status_code == 200, json
        assert json['status'] == 'ok'
        assert json['message'] == 'User Is Now Active'


class TestLogin:
    '''Test Login
    '''
    def test_incomplete_data(self, client):
        # Login with incomplete data
        rv = client.post('/auth/session', json={})
        json = rv.get_json()
        assert rv.status_code == 400
        assert json['status'] == 'err'
        assert json['message'] == 'Requested Value With Wrong Type'

    def test_wrong_password(self, client):
        # Login with wrong password
        rv = client.post(
            '/auth/session',
            json={
                'username': 'test',
                'password': 'tset'
            },
        )
        json = rv.get_json()
        assert rv.status_code == 401
        assert json['status'] == 'err'
        assert json['message'] == 'Login Failed'

    @pytest.mark.skip(reason='User\'s active is set to `True` by deafult')
    def test_not_active(self, client):
        password = 'ju5t_a_p4ssw0rd'
        u = utils.user.lazy_signup(password=password)
        # Login an inactive user
        rv = client.post(
            '/auth/session',
            json={
                'school': u.school,
                'username': u.username,
                'password': password,
            },
        )
        json = rv.get_json()
        assert rv.status_code == 401, json
        assert json['status'] == 'err', json
        assert json['message'] == 'Inactive User', json

    def test_with_username_and_school(self, client):
        password = secrets.token_urlsafe()
        u = utils.user.lazy_signup(password=password)
        # Login with username
        rv = client.post(
            '/auth/session',
            json={
                'school': u.school,
                'username': u.username,
                'password': password,
            },
        )
        json = rv.get_json()
        assert rv.status_code == 200, json
        assert json['status'] == 'ok', json
        assert json['message'] == 'Login Success', json

    def test_with_email(self, client):
        email = f'{secrets.token_hex(8)}@noj.tw'
        password = secrets.token_urlsafe()
        u = utils.user.lazy_signup(
            email=email,
            password=password,
        )
        # Login with email
        rv = client.post(
            '/auth/session',
            json={
                'email': email,
                'password': password,
            },
        )
        json = rv.get_json()
        assert rv.status_code == 200, json
        assert json['status'] == 'ok', json
        assert json['message'] == 'Login Success', json


class TestLogout:
    '''Test Logout
    '''
    def test_logout(self, client):
        u = utils.user.lazy_signup()
        # Logout
        client.set_cookie('test.test', 'piann', u.secret)
        rv = client.get('/auth/session')
        json = rv.get_json()
        assert rv.status_code == 200
        assert json['status'] == 'ok'
        assert json['message'] == 'Goodbye'


def test_token_refresh(client: FlaskClient):
    u = utils.user.lazy_signup()
    # test token can correctly work
    client.set_cookie('test.test', 'piann', u.secret)
    rv = client.post('/auth/check/token')
    assert rv.status_code == 200
    # make an invalid token
    token = jwt_decode(u.secret)
    token['data']['_id'] = 'n0t_A_Valid_1d'
    token = jwt.encode(
        token,
        key=b'An0ther53cretKeY',
    )
    # refresh token
    client.set_cookie('test.test', 'piann', token)
    rv = client.post(
        '/auth/check/token',
        follow_redirects=True,
    )
    rv_json = rv.get_json()
    assert rv.status_code == 200, rv_json
    assert rv_json['message'] == 'Goodbye'
    # TODO: check cookie value


def test_batch_signup_nonexist_user(forge_client: Callable[[], FlaskClient]):
    register_fields = {
        'username',
        'school',
        'password',
        'displayName',
    }
    u_data = utils.user.data()
    u_data['displayName'] = u_data['username']
    u_data = partial_dict(
        u_data,
        register_fields,
    )
    # convert dict to csv string
    csv_io = io.StringIO()
    writer = csv.DictWriter(csv_io, register_fields)
    writer.writeheader()
    writer.writerow(u_data)
    csv_string = csv_io.getvalue()
    c = utils.course.lazy_add()
    client = forge_client(c.teacher.username)
    rv = client.post(
        '/auth/batch-signup',
        json={
            'csvString': csv_string,
            'course': str(c.id),
        },
    )
    assert rv.status_code == 200
    # ensure the user is registered
    u = User.get_by_username(u_data['username'])
    assert u
    assert User.login(u.school, u.username, u_data['password']) == u
    assert c in u.courses, (c.name, [c.name for c in u.courses])
