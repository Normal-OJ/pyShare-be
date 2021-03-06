import pytest
from mongo import *
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def test_login():
    password = 'verysecureandlongpassword'
    u = utils.user.lazy_signup(password=password)
    assert User.login(u.username, password) == u
    assert User.login(u.email, password) == u


def test_login_fail():
    password = 'verysecureandlongpassword'
    u = utils.user.lazy_signup(password=password)
    with pytest.raises(DoesNotExist):
        User.login(u.username, password[::-1])
    with pytest.raises(DoesNotExist):
        User.login(u.email, password[::-1])


def test_change_password():
    password = 'verysecureandlongpassword'
    new_password = 'unsafepassword'
    u = utils.user.lazy_signup(password=password)
    u.change_password(new_password)
    assert User.login(u.username, new_password) == u
    with pytest.raises(DoesNotExist):
        assert User.login(u.username, password) == u
