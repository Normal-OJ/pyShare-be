import secrets
from typing import Optional, List
from flask.testing import FlaskClient
from pymongo.common import RETRY_WRITES
from werkzeug.datastructures import FileStorage
from mongo.submission import Submission
from mongo.problem import Problem
from mongo.comment import Comment
from mongo.user import User
from mongo.sandbox import ISandbox
from mongo.utils import doc_required
from . import problem as problem_lib
from . import user as user_lib
from . import comment as comment_lib
from . import course as course_lib


class Payload:
    def __init__(
            self,
            stdout: str = '',
            stderr: str = '',
            token: Optional[str] = None,
            files: List[FileStorage] = [],
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.token = token
        self.files = files

    def to_dict(self):
        return {
            k: getattr(self, k)
            for k in ('stdout', 'stderr', 'token', 'files')
        }


class MockSandbox(ISandbox):
    _instance = None
    store = {}

    def __new__(cls) -> 'MockSandbox':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        super().__init__()

    @doc_required('submission', Submission)
    def send(self, submission: Submission) -> bool:
        return True

    def set_payload(
        self,
        _id: str,
        payload: Payload,
    ):
        pass

    def complete(
        self,
        _id: str,
        client: Optional[FlaskClient] = None,
        payload: Optional[Payload] = None,
    ):
        if payload is None:
            payload = self.store.get(_id)
        return client.put(
            f'/submission/{_id}/complete',
            data=payload.to_dict(),
        )


def lazy_add_new(
    user: Optional[User] = None,
    problem: Optional[Problem] = None,
    code: Optional[str] = None,
    test_submission: bool = False,
):
    if user is None:
        user = user_lib.Factory.student()
    if problem is None:
        course = course_lib.lazy_add()
        course.add_student(user)
        problem = problem_lib.lazy_add(course=course)
    if code is None:
        code = f'print("{secrets.token_hex()}")'
    if test_submission:
        return Submission.add(
            problem=problem,
            user=user,
            comment=None,
            code=code,
        )
    comment = comment_lib.lazy_add_comment(
        author=user,
        problem=problem,
        code=code,
    )
    return Submission(comment.submission)
