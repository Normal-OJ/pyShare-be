import secrets
from mongo import *


def random_username():
    return secrets.token_hex(8)


def data(
    username=None,
    password=None,
    email=None,
    has_email=True,
):
    if username is None:
        username = random_username()
    if password is None:
        password = secrets.token_urlsafe()
    if email is None and has_email:
        email = f'{random_username()}@pyshare.noj.tw'
    return {
        'username': username,
        'password': password,
        'email': email,
    }


def lazy_signup(**ks):
    return User.signup(**data(**ks))


def randomly_add():
    return lazy_signup()
