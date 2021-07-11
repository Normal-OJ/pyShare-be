import hashlib
import json
import os
from functools import wraps
from bson import ObjectId
import redis
from . import engine
from .config import ConfigLoader

__all__ = [
    'hash_id',
    'doc_required',
    'Enum',
    'to_bool',
    'ObjectIdEncoder',
    'get_redis_client',
]


class Enum:
    @staticmethod
    def is_private(property_name: str):
        return property_name.startswith('__')

    @classmethod
    def items(cls):
        return [(key, val) for key, val in cls.__dict__.items()
                if not cls.is_private(key)]

    @classmethod
    def choices(cls):
        return [val for key, val in cls.items()]


def hash_id(salt, text):
    text = ((salt or '') + (text or '')).encode()
    sha = hashlib.sha3_512(text)
    return sha.hexdigest()[:24]


def to_bool(s: str):
    if s == 'true':
        return True
    elif s == 'false':
        return False
    else:
        raise TypeError


def doc_required(
    src,
    des,
    cls=None,
    null=False,
):
    '''
    query db to inject document into functions.
    if the document does not exist in db, raise `engine.DoesNotExist`.
    if `src` not in parameters, this funtcion will raise `TypeError`
    `doc_required` will check the existence of `des` in `func` parameters,
    if `des` is exist, this function will override it, so `src == des`
    are acceptable
    '''
    # user the same name for `src` and `des`
    # e.g. `doc_required('user', User)` will replace parameter `user`
    if cls is None:
        cls = des
        des = src

    def deco(func):
        @wraps(func)
        def wrapper(*args, **ks):
            # try get source param
            if src not in ks:
                raise TypeError(f'{src} not found in function argument')
            src_param = ks.get(src)
            # convert it to document
            # TODO: add type checking, whether the cls is a subclass of `MongoBase`
            #       or maybe it is not need
            if type(cls) != type(int):
                raise TypeError('cls must be a type')
            # process `None`
            if src_param is None:
                if not null:
                    raise ValueError('src can not be None')
                doc = None
            elif not isinstance(src_param, cls):
                doc = cls(src_param)
            # or, it is already target class instance
            else:
                doc = src_param
            # not None and non-existent
            if doc is not None and not doc:
                raise engine.DoesNotExist(f'{doc} not found!')
            # replace original paramters
            del ks[src]
            # FIXME: current_logger is not defined
            if des in ks:
                current_app.logger.warning(
                    f'replace a existed argument in {func}')
            ks[des] = doc
            return func(*args, **ks)

        return wrapper

    return deco


class ObjectIdEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)


# Fake redis server
server = None
# Redis connection pool
redis_pool = None


def get_redis_client():
    # Only import fakeredis in testing environment
    if ConfigLoader.get('TESTING') == True:
        import fakeredis
        global server
        if server is None:
            server = fakeredis.FakeServer()
        return fakeredis.FakeStrictRedis(server=server)
    else:
        # Create connection pool
        global redis_pool
        if redis_pool is None:
            redis_pool = redis.ConnectionPool(
                host=os.getenv('REDIS_HOST'),
                port=os.getenv('REDIS_PORT'),
                db=0,
            )
        return redis.Redis(connection_pool=redis_pool)
