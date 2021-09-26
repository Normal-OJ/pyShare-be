import io
import secrets
from tests import utils
from mongo.comment import Comment
from mongo.submission import Submission
from mongo.sandbox import ISandbox
from werkzeug.datastructures import FileStorage
import zipfile


def setup_function(_):
    ISandbox.use(utils.submission.MockSandbox)
    utils.mongo.drop_db()


def teardown_function(_):
    ISandbox.use(None)


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
    assert submission.result.stdout == 'output'
    assert submission.result.stderr == 'err'


def test_get_files():
    problem = utils.problem.lazy_add(allow_multiple_comments=True)
    submission = utils.submission.lazy_add_new(problem=problem)
    files = {secrets.token_hex(3): secrets.token_bytes() for _ in range(10)}
    for name in files:
        try:
            submission.get_file(name)
        except Submission.Pending:
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


def test_complete_multiple():
    problem = utils.problem.lazy_add(allow_multiple_comments=True)
    submission = utils.submission.lazy_add_new(problem=problem)
    except_outputs = ((secrets.token_hex(), secrets.token_hex())
                      for _ in range(10))
    for out, err in except_outputs:
        submission.complete(
            files=[],
            stderr=err,
            stdout=out,
            judge_result=0,
        )
        assert submission.result.stdout == out
        assert submission.result.stderr == err


def test_oj_problem_has_accepted_shoulde_update():
    problem = utils.problem.lazy_add(
        allow_multiple_comments=True,
        is_oj=True,
    )
    submission = utils.submission.lazy_add_new(problem=problem)
    submission.complete(
        files=[],
        stderr='err',
        stdout='output',
        judge_result=Submission.engine.JudgeResult.AC,
    )
    Comment(submission.comment).finish_submission()
    submission.reload('comment')
    assert submission.result.judge_result == Submission.engine.JudgeResult.AC
    assert submission.comment.has_accepted == True


def test_oj_problem_file_is_correct():
    problem = utils.problem.lazy_add(
        allow_multiple_comments=True,
        is_oj=True,
        input='in',
        output='out',
    )

    with problem.OJ_file() as tmp_f:
        with zipfile.ZipFile(tmp_f) as zip_ref:
            assert zip_ref.read('input') == b'in'
            assert zip_ref.read('output') == b'out'
