import secrets
from typing import Optional
from mongo import *
from mongo import engine
from .utils import drop_none

__all__ = ('data', 'lazy_signup', 'Factory')


def random_username():
    return secrets.token_hex(8)


# TODO: use enum to define role
def data(
    username: Optional[str] = None,
    password: Optional[str] = None,
    school=None,
    email: Optional[str] = None,
    has_email=True,
    role: Optional[int] = None,
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


# TODO: use enum to define role
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
