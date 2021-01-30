import pytest
from mongo import *
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def test_login():
    password = 'verysecureandlongpassword'
    email = 'email@noj.tw'
    u = utils.user.lazy_signup(password=password, email=email)
    assert User.login(u.username, password) == u
    assert User.login(u.email, password) == u


def test_login_fail():
    password = 'verysecureandlongpassword'
    email = 'email@noj.tw'
    u = utils.user.lazy_signup(password=password, email=email)
    with pytest.raises(DoesNotExist, match=''):
        User.login(u.username, password[::-1])
    with pytest.raises(DoesNotExist, match=''):
        User.login(u.email, password[::-1])


def test_change_password():
    password = 'verysecureandlongpassword'
    new_password = 'unsafepassword'
    u = utils.user.lazy_signup(password=password)
    u.change_password('unsafepassword')
    assert User.login(u.username, new_password) == u
    with pytest.raises(DoesNotExist):
        assert User.login(u.username, password) == u
