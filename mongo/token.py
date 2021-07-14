import secrets
from .utils import get_redis_client

__all__ = (
    'TokenExistError',
    'Token',
)

class TokenExistError(Exception):
    def __init__(self, _id: str) -> None:
        self.id = _id
        super().__init__(f'Token for {_id} exists')

class Token:
    def __init__(self, val=None):
        self._client = get_redis_client()
        if val is None:
            val = self.gen()
        self.val = val

    @staticmethod
    def gen():
        return secrets.token_urlsafe()

    def assign(self, submission_id):
        '''
        assign a token to submission, if no token provided
        generate a random one
        '''
        # only accept one pending submission
        if self._client.exists(submission_id):
            raise TokenExistError(submission_id)
        self._client.set(submission_id, self.val, ex=600)
        return self.val

    def verify(self, submission_id):
        # no token found
        if not self._client.exists(submission_id):
            return False
        # get submission token
        s_token = self._client.get(submission_id).decode('ascii')
        result = secrets.compare_digest(s_token, self.val)
        # delete if success
        if result is True:
            self._client.delete(submission_id)
        return result
