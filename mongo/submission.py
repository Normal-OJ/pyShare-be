import json
import os
import pathlib
import secrets
import requests as rq
from flask import current_app
from typing import List
import redis
import fakeredis

from . import engine
from .base import MongoBase
from .user import User
from .problem import Problem
from .utils import doc_required

__all__ = [
    'Submission',
    'Token',
    'SubmissionPending',
]

REDIS_POOL = redis.ConnectionPool(
    host=os.getenv('REDIS_HOST'),
    port=os.getenv('REDIS_PORT'),
    db=0,
)


def get_redis_client():
    if current_app.config['TESTING']:
        return fakeredis.FakeStrictRedis()
    else:
        return redis.Redis(connection_pool=REDIS_POOL)


class SubmissionPending(Exception):
    def __init__(self, _id):
        super().__init__(f'{_id} still pending.')


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
            raise SubmissionPending(submission_id)
        self._client.set(submission_id, self.val, ex=600)
        return self.val

    def verify(self, submission_id):
        # no token found
        if not self._client.exists(submission_id):
            return False
        # get submission token
        s_token = self._client.get(submission_id)
        result = secrets.compare_digest(s_token, self.val)
        # delete if success
        if result is True:
            self._client.delete(submission_id)
        return result


class Submission(MongoBase, engine=engine.Submission):
    JUDGE_URL = os.getenv(
        'JUDGE_URL',
        'http://sandbox:1450',
    )
    SANDBOX_TOKEN = os.getenv(
        'SANDBOX_TOKEN',
        '14508888',
    )

    def __init__(self, _id):
        self.id = str(_id)

    @property
    def problem_id(self):
        return self.problem.problem_id

    def to_dict(self):
        _ret = {
            'problemId': self.problem.problem_id,
            'user': User(self.user.username).info,
            'submissionId': self.id,
            'timestamp': self.timestamp.timestamp()
        }
        ret = json.loads(self.obj.to_json())

        old = [
            '_id',
            'problem',
        ]
        for o in old:
            del ret[o]

        for n in _ret.keys():
            ret[n] = _ret[n]

        return ret

    def delete(self):
        if not self:
            raise engine.DoesNotExist(f'{self}')
        # delete files
        if self.result is not None:
            for f in self.result.files:
                f.delete()
        # delete document
        self.obj.delete()

    def submit(self) -> bool:
        '''
        prepara data for submit code to sandbox and then send it
        '''
        # unexisted id
        if not self:
            raise engine.DoesNotExist(f'{self}')
        token = Token(self.SANDBOX_TOKEN).assign(self.id)
        judge_url = f'{self.JUDGE_URL}/{self.id}'
        # send submission to snadbox for judgement
        resp = rq.post(
            f'{judge_url}?token={token}',
            files={
                'attachments':
                [(a.filename, a, None) for a in self.problem.attachments]
            },
            data={
                'src': self.code,
            },
        )
        return True

    def complete(
        self,
        files,
        stderr: str,
        stdout: str,
    ):
        '''
        judgement complete
        '''
        # create files
        files = [self.new_file(f.filename, f.read()) for f in files]
        # update status
        self.update(status=0)
        # update result
        self.result.update(
            stdout=stdout,
            stderr=stderr,
            files=files,
        )
        # notify user
        user.add_submission(self.reload())
        return True

    @staticmethod
    def new_file(filename, data):
        '''
        create a new file
        '''
        f = engine.GridFSProxy()
        f.put(
            filename=filename,
            data=data,
        )
        f.save()
        return f

    @classmethod
    @doc_required('problem', Problem)
    @doc_required('user', User)
    def add(
            cls,
            problem: Problem,
            user: User,
            code: str,
    ) -> 'Submission':
        '''
        Insert a new submission into db

        Returns:
            The created submission
        '''
        submission = engine.Submission(
            problem=problem.obj,
            user=user.obj,
            code=code,
        )
        submission.save()
        return cls(submission.id)
