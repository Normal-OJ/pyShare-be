from mongo import engine
from flask import Blueprint, request
from mongo import *
from .utils import *

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


@submission_api.route('/', methods=['POST'])
@login_required
@Request.json(
    'code: str',
    'problem_id',
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
    return HTTPResponse('Submission recieved.')


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
