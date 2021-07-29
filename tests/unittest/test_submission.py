import io
import secrets
from tests import utils
from mongo.submission import Submission, SubmissionPending
from werkzeug.datastructures import FileStorage


def setup_function(_):
    utils.mongo.drop_db()


def test_add():
    submission = Submission.add(
        problem=utils.problem.lazy_add(),
        user=utils.user.Factory.student(),
        code='print("test")',
        comment=None,
    )
    assert submission


def test_complete():
    problem = utils.problem.lazy_add(allow_multiple_comments=True)
    submission = utils.submission.lazy_add_new(problem=problem)
    submission.complete(
        files=[],
        stderr='err',
        stdout='output',
        judge_result=0,
    )


def test_get_files():
    problem = utils.problem.lazy_add(allow_multiple_comments=True)
    submission = utils.submission.lazy_add_new(problem=problem)
    files = {secrets.token_hex(3): secrets.token_bytes() for _ in range(10)}
    for name in files:
        try:
            submission.get_file(name)
        except SubmissionPending:
            continue
        assert False
    submission.complete(
        files=[
            FileStorage(
                io.BytesIO(content),
                filename=name,
            ) for name, content in files.items()
        ],
        stderr='err',
        stdout='output',
        judge_result=0,
    )
    for name, content in files.items():
        file = submission.get_file(name)
        assert file.read() == content
