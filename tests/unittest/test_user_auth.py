import pytest
from mongo import *
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def test_login():
    password = 'verysecureandlongpassword'
    u = utils.user.lazy_signup(password=password)
    assert User.login(u.school, u.username, password) == u
    assert User.login_by_email(u.email, password) == u


def test_login_fail():
    password = 'anoth3rverys3cureandmorelongpassword'
    u = utils.user.lazy_signup(password=password)
    # TODO: test email login
    with pytest.raises(DoesNotExist):
        User.login(
            u.school,
            u.username,
            password[::-1],
        )
    with pytest.raises(DoesNotExist):
        User.login_by_email(
            u.email,
            password[::-1],
        )


def test_change_password():
    password = 'yetanotherverysecureandmoremorelongpasswordthatidontwanttotypetwice'
    new_password = 'shortpassword'
    u = utils.user.lazy_signup(password=password)
    u.change_password(new_password)
    assert User.login(
        u.school,
        u.username,
        new_password,
    ) == u
    assert User.login_by_email(
        u.email,
        new_password,
    ) == u
    with pytest.raises(DoesNotExist):
        assert User.login(
            u.school,
            u.username,
            password,
        ) == u
    with pytest.raises(DoesNotExist):
        assert User.login_by_email(
            u.email,
            password,
        ) == u
