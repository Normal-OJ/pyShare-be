from mongoengine import connect, disconnect
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

    @classmethod
    def drop_db(cls):
        disconnect()
        conn = connect(cls.DB, host=cls.MONGO_HOST)
        conn.drop_database(cls.DB)

    @classmethod
    def setup_class(cls):
        cls.drop_db()

    @classmethod
    def teardown_class(cls):
        cls.drop_db()

    @staticmethod
    def request(client, method, url, **ks):
        func = getattr(client, method)
        rv = func(url, **ks)
        rv_json = rv.get_json()
        rv_data = rv_json['data']

        return rv, rv_json, rv_data
