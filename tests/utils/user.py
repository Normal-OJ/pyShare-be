import secrets
from typing import Optional
from mongo import *
from .utils import drop_none

__all__ = ('data', 'lazy_signup')


def random_username():
    return secrets.token_hex(8)


def data(
    username: Optional[str] = None,
    password: Optional[str] = None,
    email: Optional[str] = None,
    role: Optional[int] = None,
):
    if username is None:
        username = random_username()
    if password is None:
        password = secrets.token_urlsafe()
    if email is None:
        email = f'{secrets.token_hex(8)}@noj.tw'
    return drop_none({
        'username': username,
        'password': password,
        'email': email,
        'role': role,
    })


def lazy_signup(**ks):
    return User.signup(**data(**ks))
