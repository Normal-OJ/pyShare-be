import pytest
from mongo import *
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def test_normally_signup():
    utils.user.lazy_signup()


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
            match=r'.*Duplicate.*',
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
        utils.user.lazy_signup(email=email)


def test_email_case_sensitivity():
    User.signup(**utils.user.data(email='bogay@noj.tw'))
    with pytest.raises(
            NotUniqueError,
            match=r'.*Duplicate.*',
    ):
        utils.user.lazy_signup(email='BogAy@nOj.tw')


def test_email_strip_space():
    email = ' email@with.space  '
    u = utils.user.lazy_signup(email=email)
    assert u.email == email.strip()


def test_long_username():
    with pytest.raises(
            ValidationError,
            match=r'.*long.*',
    ):
        utils.user.lazy_signup(username='a' * 32)


def test_multiple_users_have_no_email():
    users = [utils.user.lazy_signup(has_email=False) for _ in range(5)]
    assert all(u.email is None for u in users)


def test_update_email_uniqueness():
    email = 'bogay@noj.tw'
    utils.user.lazy_signup(email=email)
    u = utils.user.lazy_signup()
    with pytest.raises(
            NotUniqueError,
            match=r'.*Duplicate.*email.*',
    ):
        u.update(email=email)


def test_update_email_also_change_md5():
    email = 'bogay@noj.tw'
    u = utils.user.lazy_signup(email=email)
    assert u.md5 == u.email_hash(email), (u.md5, u.email)
    email = 'not.bogay@noj.tw'
    u.update(email=email)
    u.reload('email', 'md5')
    assert u.md5 == u.email_hash(email), (u.md5, u.email)


def test_cannot_signup_with_empty_password():
    with pytest.raises(ValueError):
        utils.user.lazy_signup(password='')
