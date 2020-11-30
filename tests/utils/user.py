import secrets
from mongo import *


def random_username():
    return secrets.token_hex(8)


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
