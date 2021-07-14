import os
import io
import tempfile
from abc import ABC, abstractmethod
from zipfile import ZipFile
import requests as rq
from .utils import doc_required
from .submission import Submission
from .token import Token

__all__ = (
    'ISandbox',
    'Sandbox',
    'MockSandbox',
)


class ISandbox(ABC):
    cls = None

    @abstractmethod
    def send(self, submission: Submission) -> bool:
        raise NotImplementedError

    @classmethod
    def use(cls, _cls):
        if not issubclass(_cls, ISandbox):
            raise TypeError('It shoud be a subclass of ISandbox')
        cls.cls = _cls


class Sandbox(ISandbox):
    JUDGE_URL = os.getenv(
        'JUDGE_URL',
        'http://sandbox:1450',
    )
    SANDBOX_TOKEN = os.getenv(
        'SANDBOX_TOKEN',
        'KoNoSandboxDa',
    )

    @doc_required('submission', Submission)
    def send(self, submission: Submission) -> bool:
        # Extract problem attachments
        files = [(
            'attachments',
            (a.filename, a, None),
        ) for a in submission.problem.attachments]
        # Attatch standard input / output
        if submission.problem.is_OJ:
            with tempfile.TemporaryFile() as tmp_f:
                with ZipFile(tmp_f, 'w') as zf:
                    # Add multiple files to the zip
                    zf.writestr('input', submission.problem.extra.input)
                    zf.writestr('output', submission.problem.extra.output)
                with open(tmp_f.name, 'rb') as f:
                    files.append(('testcase', (
                        tmp_f.name,
                        io.BytesIO(f.read()),
                        None,
                    )))
        token = Token(self.SANDBOX_TOKEN).assign(submission.id)
        try:
            resp = rq.post(
                f'{self.JUDGE_URL}/{submission.id}',
                params={'token': token},
                files=files,
                data={'src': submission.code},
            )
        except rq.exceptions.RequestException as e:
            return False
        else:
            if not resp.ok:
                pass
            return True


class MockSandbox(ISandbox):
    pass