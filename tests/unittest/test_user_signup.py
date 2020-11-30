import pytest
from mongo import *
from mongo import engine
from tests import utils


def test_normally_signup():
    _id = utils.user.random_username()
    utils.user.lazy_signup(_id)


def test_not_unique():
    _id = utils.user.random_username()
    utils.user.lazy_signup(_id)
    with pytest.raises(
            NotUniqueError,
            match=r'.*duplicate.*',
    ):
        utils.user.lazy_signup(_id)


def test_invalid_email():
    USER_DATA = {
        'username': utils.user.random_username(),
        'password': 'a_very_l0ng_And_sTR04G_pazzw0rd',
        'email': 'invalid_email',
    }
    with pytest.raises(
            ValidationError,
            match=r'.*email.*',
    ):
        User.signup(**USER_DATA)
