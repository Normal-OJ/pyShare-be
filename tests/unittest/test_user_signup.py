import pytest
from mongo import *
from tests import utils


def setup_function(function):
    utils.mongo.drop_db()


def test_normally_signup():
    utils.user.randomly_add()


@pytest.mark.parametrize(
    'field, value',
    [
        ('username', 'bogay'),
        ('email', 'bogay@noj.tw'),
        # password can be the same
        pytest.param(
            'password',
            'A_v3ry_l0Ng_And_Str0NG_passw0rd',
            marks=pytest.mark.xfail,
        )
    ],
)
def test_not_unique(field, value):
    User.signup(**utils.user.data(**{field: value}))
    with pytest.raises(
            NotUniqueError,
            match=r'.*duplicate.*',
    ):
        User.signup(**utils.user.data(**{field: value}))


def test_invalid_email():
    with pytest.raises(
            ValidationError,
            match=r'.*email.*',
    ):
        User.signup(**utils.user.data(email='invalid_email'))


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