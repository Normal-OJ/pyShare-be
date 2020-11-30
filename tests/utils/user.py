import secrets
from mongo import *


def random_username():
    return secrets.token_hex(8)


def data(
    username=None,
    password=None,
    email=None,
):
    if username is None:
        username = random_username()
    if password is None:
        password = secrets.token_urlsafe()
    if email is None:
        email = f'{secrets.token_hex(8)}@noj.tw'
    return {
        'username': username,
        'password': password,
        'email': email,
    }


def lazy_signup(_id=None):
    if _id is None:
        _id = random_username()
    User.signup(
        username=_id,
        password=f'password_for_{_id}',
        email=f'{_id}@noj.tw',
    )


def randomly_add():
    lazy_signup()
