from typing import Optional, List
from flask.testing import FlaskClient
from werkzeug.datastructures import FileStorage
from mongo.submission import Submission
from mongo.sandbox import ISandbox
from mongo.utils import doc_required, get_redis_client


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
