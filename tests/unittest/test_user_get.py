import pytest
from mongo import *
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


@pytest.mark.parametrize(
    'username, query',
    [
        ('bogay', 'bogay'),
        ('bogay', 'b0gay'),
        ('bogay', 'BOGAY'),
        ('bogay', 'Bogay'),
    ],
)
def test_get_by_username(username, query):
    u = utils.user.lazy_signup(username=username)
    try:
        assert User.get_by_username(query) == u
    except DoesNotExist:
        assert query != username


@pytest.mark.parametrize(
    'email, query, equal',
    [
        ('bogay@noj.tw', 'bogay@noj.tw', True),
        ('bogay@noj.tw', 'BoGAy@Noj.TW', True),
        ('bogay@noj.tw', 'b0gay@noj.tw', False),
        ('bogay@noj.tw', 'bogay.dev@noj.tw', False),
        ('bogay@noj.tw', 'bogay@noj.tw.', False),
        ('bogay@noj.tw', 'bogay@pyshare.noj.tw', False),
    ],
)
def test_get_by_email(email, query, equal):
    u = utils.user.lazy_signup(email=email)
    try:
        assert User.get_by_email(query) == u
    except DoesNotExist:
        assert not equal


def test_can_not_get_email_with_none():
    utils.user.lazy_signup(has_email=False)
    with pytest.raises(DoesNotExist):
        User.get_by_email(None)
