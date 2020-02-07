from mongoengine import connect
from mongo import *
from mongo import engine
from mongo import problem
from .conftest import *

import random
import string
import secrets


def random_string(k=32):
    '''
    return a random string contains only lower and upper letter wieh length k

    Args:
        k: the return string's length, default is 32

    Returns:
        a random-generated string with length k
    '''

    return secrets.token_hex()[:k]


class BaseTester:
    MONGO_HOST = 'mongomock://localhost'
    DB = 'normal-oj'
    USER_CONFIG = 'tests/user.json'

    @classmethod
    def drop_db(cls):
        conn = connect(cls.DB, host=cls.MONGO_HOST)
        conn.drop_database(cls.DB)
        problem.number = 1

    @classmethod
    def setup_class(cls):
        cls.drop_db()

        with open(cls.USER_CONFIG) as f:
            import json
            config = json.load(f)
            users = {}
            tcls = cls
            while True:
                users.update(config.get(tcls.__name__, {}))
                if tcls.__name__ == 'BaseTester':
                    break
                tcls = tcls.__base__

            for name, role in users.items():
                cls.new_user(name, role)

        if Number("serial_number").obj is None:
            engine.Number(name="serial_number").save()

    @classmethod
    def teardown_class(cls):
        cls.drop_db()

    @classmethod
    def new_user(cls, username, role):
        USER = {
            'username': username,
            'password': f'{username}_password',
            'email': f'i.am.{username}@noj.tw'
        }

        user = User.signup(**USER)
        user.update(active=True,
                    role=role,
                    profile={
                        'displayedName': '',
                        'bio': ''
                    })

    @staticmethod
    def request(client, method, url, **ks):
        func = getattr(client, method)
        rv = func(url, **ks)
        rv_json = rv.get_json()
        rv_data = rv_json['data']

        return rv, rv_json, rv_data
