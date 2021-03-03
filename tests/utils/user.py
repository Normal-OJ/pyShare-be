import secrets
from typing import Optional
from mongo import *
from .utils import drop_none

__all__ = ('data', 'lazy_signup', 'Factory')


def random_username():
    return secrets.token_hex(8)


# TODO: use enum to define role
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


# TODO: use enum to define role
class Factory:
    @staticmethod
    def admin():
        return lazy_signup(role=0)

    @staticmethod
    def teacher():
        return lazy_signup(role=1)

    @staticmethod
    def student():
        return lazy_signup()
