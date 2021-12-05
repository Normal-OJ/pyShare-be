from typing import List, Optional
import base64
from blinker import signal
from . import engine
from .base import MongoBase
from .user import User
from .problem import Problem
from .comment import Comment
from .utils import doc_required, get_redis_client
from .token import TokenExistError

__all__ = ('Submission', )


class Submission(MongoBase, engine=engine.Submission):
    on_complete = signal('submission_completed')

    class Pending(Exception):
        def __init__(self, _id):
            super().__init__(f'{_id} still pending.')

    @property
    def problem_id(self):
        return self.problem.problem_id

    def to_dict(self):
        '''
        return serialized submission
        '''
        if not self:
            return {}
        ret = {
            'code': self.code,
            'state': self.state,
            'timestamp': self.timestamp.timestamp(),
        }
        if self.result is not None:
            ret.update({
                'stdout': self.result.stdout,
                'stderr': self.result.stderr,
                'files': [f.filename for f in self.result.files],
                'judge_result': self.result.judge_result,
            })
        return ret

    def extract(self, _delete=True):
        '''
        deeply serialize submission, include file content instead of only containing files' name.
        '''
        ret = self.to_dict()
        if self.result is not None:
            files = [{
                'filename': f.filename,
                'content': base64.b64encode(f.read()).decode('ascii'),
            } for f in self.result.files]
            ret.update({
                'stdout': self.result.stdout,
                'stderr': self.result.stderr,
                'files': files,
            })
            if _delete:
                self.delete()
        return ret

    def clear(self):
        # delete files
        if self.result is not None:
            for f in self.result.files:
                f.delete()

    def delete(self):
        if not self:
            raise engine.DoesNotExist(f'{self}')
        # delete document
        self.clear()
        self.obj.delete()

    def submit(self) -> bool:
        '''
        prepara data for submit code to sandbox and then send it
        '''
        # nonexistent id
        if not self:
            raise engine.DoesNotExist(f'{self}')
        self.update(status=self.engine.Status.PENDING)
        # send submission to snadbox for judgement
        from .sandbox import ISandbox
        try:
            return ISandbox.cls().send(submission=self)
        except TokenExistError as e:
            raise self.Pending(e.id)

    def complete(
        self,
        files: List,
        stderr: str,
        stdout: str,
        judge_result,
    ):
        '''
        judgement complete
        '''
        with get_redis_client().lock(f'{self}'):
            result = self.engine.Result(
                stdout=stdout,
                stderr=stderr,
                judge_result=judge_result,
            )
            self.update(
                result=result,
                status=self.engine.Status.COMPLETE,
            )
            files = [self.new_file(
                f,
                filename=f.filename,
            ) for f in files]
            self.reload('result', 'status')
            self.result.files = files
            self.save()
            self.on_complete.send(self.reload())
        return True

    def get_file(self, filename):
        if self.result is None:
            raise self.Pending(self.id)
        for f in self.result.files:
            if f.filename == filename:
                return f
        raise FileNotFoundError(filename)

    @staticmethod
    def new_file(file_obj, filename):
        '''
        create a new file
        '''
        # TODO: this is almost identical to Problem.new_att, may be can write this ot utils
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
    @doc_required('comment', Comment, null=True)
    def add(
        cls,
        problem: Problem,
        user: User,
        comment: Optional[Comment],
        code: str,
    ) -> 'Submission':
        '''
        Insert a new submission into db

        Returns:
            The created submission
        '''
        # TODO: Validate the relation of user, problem and comment
        submission = engine.Submission(
            problem=problem.obj,
            user=user.obj,
            comment=getattr(comment, 'obj', None),
            code=code,
        )
        submission.save()
        return cls(submission.id)
