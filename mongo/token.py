import abc
import secrets
import redis
import fakeredis
from flask import current_app
from .submission import *

REDIS_POOL = redis.ConnectionPool(
    host=os.getenv('REDIS_HOST'),
    port=os.getenv('REDIS_PORT'),
    db=0,
)

__all__ = [
    'DictToken',
    'RedisToken',
]


class TokenBase(abc.ABC):
    def __init__(self, val=None):
        if val is None:
            val = self.gen()
        self.val = val

    @staticmethod
    def gen():
        return secrets.token_urlsafe()

    @abc.abstractmethod
    def assign(self, submission_id):
        raise NotImplementedError

    @abc.abstractmethod
    def verify(self, submission_id):
        raise NotImplementedError


class DictToken(TokenBase):
    pool = {}

    def __init__(self, val=None):
        super().__init__(val)

    def assign(self, submission_id):
        if submission_id in self.pool:
            raise SubmissionPending(submission_id)
        self.pool[submission_id] = self.val
        return self.val

    def verify(self, submission_id):
        if submission_id not in self.pool:
            return False
        result = secrets.compare_digest(self.val, self.pool[submission_id])
        if result is True:
            del self.pool[submission_id]
        return result


def get_redis_client():
    if current_app.config['TESTING']:
        return fakeredis.FakeStrictRedis()
    else:
        return redis.Redis(connection_pool=REDIS_POOL)


class RedisToken(TokenBase):
    def __init__(self, val=None):
        super().__init__(val)
        self._client = get_redis_client()

    def assign(self, submission_id):
        '''
        assign a token to submission, if no token provided
        generate a random one
        '''
        # only accept one pending submission
        if self._client.exists(submission_id):
            raise SubmissionPending(submission_id)
        self._client.set(submission_id, self.val, ex=600)
        return self.val

    def verify(self, submission_id):
        # no token found
        if not self._client.exists(submission_id):
            return False
        # get submission token
        s_token = self._client.get(submission_id).decode('ascii')
        current_app.logger.debug(f's_token type: {type(s_token)}')
        current_app.logger.debug(f'val type: {type(self.val)}')
        result = secrets.compare_digest(s_token, self.val)
        # delete if success
        if result is True:
            self._client.delete(submission_id)
        return result