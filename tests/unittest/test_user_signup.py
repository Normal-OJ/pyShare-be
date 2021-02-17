import pytest
from mongo import *
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def test_normally_signup():
    utils.user.randomly_add()


@pytest.mark.parametrize(
    'payload',
    [
        {
            'username': 'bogay',
            'school': 'NTNU',
        },
        {
            'email': 'bogay@noj.tw',
        },
        # password can be the same
        pytest.param(
            {'password': 'A_v3ry_l0Ng_And_Str0NG_passw0rd'},
            marks=pytest.mark.xfail,
        )
    ],
)
def test_not_unique(payload):
    User.signup(**utils.user.data(**payload))
    with pytest.raises(
            NotUniqueError,
            match=r'.*duplicate.*',
    ):
        User.signup(**utils.user.data(**payload))


@pytest.mark.parametrize(
    'email',
    [
        '192.168.0.1',
        'bogay＠noj.tw',
        'bogay@noj..tw',
        'A\t\t@OAO.oj',
        '$skps1450@dpp.org#bogay',
        'bogay@noj.\'tw',
    ],
)
def test_invalid_email(email):
    with pytest.raises(
            ValidationError,
            match=r'.*email.*',
    ):
        User.signup(**utils.user.data(email=email))


def test_email_case_sensitivity():
    User.signup(**utils.user.data(email='bogay@noj.tw'))
    with pytest.raises(
            NotUniqueError,
            match=r'.*duplicate.*',
    ):
        User.signup(**utils.user.data(email='BogAy@nOj.tw'))


def test_email_strip_space():
    email = ' email@with.space  '
    u = User.signup(**utils.user.data(email=email))
    assert u.email == email.strip()


def test_long_username():
    with pytest.raises(
            ValidationError,
            match=r'.*long.*',
    ):
        User.signup(**utils.user.data(username='a' * 32))
