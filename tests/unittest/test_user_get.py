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
    u = User.signup(**utils.user.data(username=username))
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
    u = User.signup(**utils.user.data(email=email))
    try:
        assert User.get_by_email(query) == u
    except DoesNotExist:
        assert not equal
