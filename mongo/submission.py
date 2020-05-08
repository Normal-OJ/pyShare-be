import json
import os
import pathlib
import logging
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
from .comment import *
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
        s_token = self._client.get(submission_id).decode('ascii')
        current_app.logger.debug(f's_token type: {type(s_token)}')
        current_app.logger.debug(f'val type: {type(self.val)}')
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
        'KoNoSandboxDa',
    )

    def __init__(self, _id):
        self.id = str(_id)

    @property
    def problem_id(self):
        return self.problem.problem_id

    def to_dict(self):
        ret = {'code': self.code}
        if self.result is not None:
            ret.update({
                'stdout': self.result.stdout,
                'stderr': self.result.stderr,
                'files': [f.filename for f in self.result.files],
            })
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
        self.update(status=-1)
        judge_url = f'{self.JUDGE_URL}/{self.id}'
        # send submission to snadbox for judgement
        resp = rq.post(
            f'{judge_url}?token={token}',
            files=[(
                'attachments',
                (a.filename, a, None),
            ) for a in self.problem.attachments],
            data={
                'src': self.code,
            },
        )
        if not resp.ok:
            logging.warning(f'got sandbox resp: {resp.text}')
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
        # update status
        self.update(status=0)
        # update result
        result = engine.SubmissionResult(
            stdout=stdout,
            stderr=stderr,
            # files=[self.new_file(f, filename=f.filename) for f in files],
        )
        self.update(result=result)
        self.reload()
        for f in files:
            f = self.new_file(f, filename=f.filename)
            self.result.files.append(f)
            self.save()
        # notify comment
        Comment(self.comment.id).finish_submission()
        return True

    @staticmethod
    def new_file(file_obj, filename):
        '''
        create a new file
        '''
        f = engine.GridFSProxy()
        f.put(
            file_obj,
            filename=filename,
        )
        # f.save()
        return f

    @classmethod
    @doc_required('problem', Problem)
    @doc_required('user', User)
    @doc_required('comment', Comment)
    def add(
            cls,
            problem: Problem,
            user: User,
            comment: Comment,
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
            comment=comment.obj,
            code=code,
        )
        submission.save()
        return cls(submission.id)
