from flask import Blueprint, request
from mongo import *
from .utils import *

__all__ = ['submission_api']

submission_api = Blueprint('submission_api', __name__)


@submission_api.route('/<_id>/complete', methods=['PUT'])
def complete(_id):
    token = request.values['token']
    submission = Submission(_id)
    if not submission.verify(token):
        return HTTPError('i don\'t know you :(', 403)
    if not submission:
        return HTTPError('submission not exists!', 404)
    files = request.files.getlist('files')
    submission.complete(
        files,
        request.values['stderr'],
        request.values['stdout'],
    )
    return HTTPResponse('ok')
