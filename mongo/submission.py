import json
import os
import pathlib
import logging
import requests as rq
from flask import current_app
from typing import List

from . import engine
from .base import MongoBase
from .user import User
from .problem import Problem
from .comment import *
from .utils import doc_required
from .token import *

__all__ = [
    'Submission',
    'SubmissionPending',
]


class SubmissionPending(Exception):
    def __init__(self, _id):
        super().__init__(f'{_id} still pending.')


class Submission(MongoBase, engine=engine.Submission):
    JUDGE_URL = os.getenv(
        'JUDGE_URL',
        'http://sandbox:1450',
    )
    SANDBOX_TOKEN = os.getenv(
        'SANDBOX_TOKEN',
        'KoNoSandboxDa',
    )
    token_cls = DictToken

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

    def verify(self, token) -> bool:
        return self.token_cls(token).verify(self.id)

    def submit(self) -> bool:
        '''
        prepara data for submit code to sandbox and then send it
        '''
        # unexisted id
        if not self:
            raise engine.DoesNotExist(f'{self}')
        token = self.token_cls(self.SANDBOX_TOKEN).assign(self.id)
        self.update(status=engine.SubmissionStatus.PENDING)
        judge_url = f'{self.JUDGE_URL}/{self.id}'
        # send submission to snadbox for judgement
        if not current_app.config['TESTING']:
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
        self.update(status=engine.SubmissionStatus.COMPLETE)
        # update result
        result = engine.SubmissionResult(
            stdout=stdout,
            stderr=stderr,
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
