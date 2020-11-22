from flask import Blueprint, request
from mongo import *
from mongo import engine
from .utils import *
from .auth import *

__all__ = ['submission_api']

submission_api = Blueprint('submission_api', __name__)


@submission_api.route('/<_id>', methods=['GET'])
@Request.doc('_id', 'submission', Submission)
def get_single(submission):
    # temporary submissions
    if submission.comment is None:
        data = submission.extract()
    # normal submissions
    else:
        data = submission.to_dict()
    return HTTPResponse(
        'here you are, bro.',
        data=data,
    )


@submission_api.route('/<_id>/file/<name>', methods=['GET'])
@login_required
@Request.doc('_id', 'submission', Submission)
def get_submission_file(
    user,
    submission: Submission,
    name,
):
    try:
        return send_file(
            submission.get_file(name),
            as_attachment=True,
            cache_timeout=1,
            attachment_filename=filename,
        )
    except FileNotFoundError:
        return HTTPError('File not found', 404)
    except SubmissionPending:
        return HTTPError('Submission is still in pending', 400)


@submission_api.route('/', methods=['POST'])
@login_required
@Request.json(
    'code: str',
    'problem_id: int',
)
@Request.doc('problem_id', 'problem', Problem)
def create_test_submission(
    user: User,
    code: str,
    problem: Problem,
):
    '''
    create a temporary submission
    '''
    try:
        submission = Submission.add(
            problem=problem,
            user=user,
            comment=None,
            code=code,
        )
    except engine.ValidationError as ve:
        return HTTPError(
            'Invalid data',
            400,
            data=ve.to_dict(),
        )
    submission.submit()
    return HTTPResponse(
        'Submission recieved.',
        data={'submissionId': str(submission.id)},
    )


@submission_api.route('/<_id>/complete', methods=['PUT'])
def complete(_id):
    token = request.values['token']
    if not Token(token).verify(_id):
        return HTTPError('i don\'t know you :(', 403)
    submission = Submission(_id)
    if not submission:
        return HTTPError(f'{submission} not exists!', 404)
    files = request.files.getlist('files')
    submission.complete(
        files,
        request.values['stderr'],
        request.values['stdout'],
    )
    return HTTPResponse('ok')


@submission_api.route('/<_id>/state', methods=['PUT'])
@login_required
@Request.json('state: int')
@Request.doc('_id', 'submission', Submission)
def change_state(user, submission: Submission, state):
    if submission.comment is None:
        return HTTPError('The submission is not in a comment.', 400)
    comment = Comment(submission.comment.id)
    if not comment.permission(user=user, req={'s'}):
        return HTTPError('Permission denied.', 403)
    try:
        submission.update(state=state)
    except engine.ValidationError as ve:
        return HTTPError(
            'Invalid data',
            400,
            data=ve.to_dict(),
        )
    comment.update(has_accepted=any(
        submission.state == engine.SubmissionState.ACCEPT
        for submission in comment.submissions))
    return HTTPResponse('ok')
