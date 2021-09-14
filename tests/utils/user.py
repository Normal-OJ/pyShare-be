import secrets
from typing import Optional
from mongo import *
from .utils import drop_none

__all__ = ('data', 'lazy_signup', 'Factory', 'random_username')


def random_username():
    return secrets.token_hex(8)


def data(
    username: Optional[str] = None,
    password: Optional[str] = None,
    school: Optional[str] = None,
    email: Optional[str] = None,
    has_email: bool = True,
    role: Optional[User.engine.Role] = None,
):
    if username is None:
        username = random_username()
    if password is None:
        password = secrets.token_urlsafe()
    if email is None and has_email:
        email = f'{random_username()}@pyshare.noj.tw'
    return drop_none({
        'username': username,
        'password': password,
        'email': email,
        'school': school,
        'role': role,
    })


def lazy_signup(**ks):
    return User.signup(**data(**ks))


class Factory:
    @staticmethod
    def admin():
        return lazy_signup(role=User.engine.Role.ADMIN)

    @staticmethod
    def teacher():
        return lazy_signup(role=User.engine.Role.TEACHER)

    @staticmethod
    def student():
        return lazy_signup()
