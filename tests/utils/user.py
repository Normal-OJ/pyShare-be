import secrets
import random
from mongo import *

SCHOOLS = [
    'NTU',
    'NTNU',
    'NTUST',
]


def random_username():
    return secrets.token_hex(8)


def data(
    username=None,
    password=None,
    email=None,
    school=None,
):
    if username is None:
        username = random_username()
    if password is None:
        password = secrets.token_urlsafe()
    if email is None:
        email = f'{secrets.token_hex(8)}@noj.tw'
    if school is None:
        school = random.choice(SCHOOLS)
    return {
        'username': username,
        'password': password,
        'email': email,
        'school': school,
    }


def lazy_signup(**ks):
    return User.signup(**data(**ks))


def randomly_add():
    return lazy_signup()
