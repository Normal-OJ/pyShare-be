from flask import Blueprint, send_file
from .utils import *
from .auth import *
from mongo import *
from mongo import engine
from datetime import datetime

__all__ = ['comment_api']

comment_api = Blueprint('comment_api', __name__)


@comment_api.route('/', methods=['POST'])
@login_required
@Request.json(
    'target: str',
    'id_',
    'title: str',
    'content: str',
    'code: str',
)
def create_comment(user, target, code, id_, **ks):
    if target == 'comment':
        try:
            comment = Comment.add_to_comment(
                target=id_,
                author=user.pk,
                **ks,
            )
        except engine.DoesNotExist:
            return HTTPError('Can not find some docuemnt', 404)
    elif target == 'problem':
        try:
            comment = Comment.add_to_problem(
                target=id_,
                code=code,
                author=user.pk,
                **ks,
            )
        except TooManyComments:
            return HTTPError('You can only have one comment', 400)
        except engine.DoesNotExist:
            return HTTPError('Can not find some docuemnt', 404)
    else:
        return HTTPError('Unknown target', 400)
    return HTTPResponse('success', data={'id': str(comment.id)})


@comment_api.route('/<_id>', methods=['GET'])
@login_required
@Request.doc('_id', 'comment', Comment)
def get_comment(user, comment: Comment):
    if not comment.permission(user=user, req={'r'}):
        return HTTPError('permission denied', 403)
    return HTTPResponse('success', data=comment.to_dict())


@comment_api.route('/<_id>', methods=['PUT'])
@Request.json(
    'content: str',
    'title: str',
)
@Request.doc('_id', 'comment', Comment)
@login_required
def modify_comment(
    user,
    comment: Comment,
    content,
    title,
):
    if not comment.permission(user=user, req={'w'}):
        return HTTPError('Permission denied.', 403)
    try:
        # update content
        comment.update(
            content=content,
            title=title,
            updated=datetime.now(),
        )
    except engine.ValidationError as ve:
        return HTTPError(
            'Invalid data',
            400,
            data=ve.to_dict(),
        )
    return HTTPResponse('success')


@comment_api.route('/<_id>/submission', methods=['POST'])
@login_required
@Request.json('code: str')
@Request.doc('_id', 'comment', Comment)
def create_new_submission(user, code, comment: Comment):
    if not comment.permission(user=user, req={'j'}):
        return HTTPError('Permission denied.', 403)
    try:
        submission = comment.add_new_submission(code)
    except NotAComment:
        return HTTPError('Only comments can has code.', 400)
    except engine.ValidationError as ve:
        return HTTPError('The source code is invalid!', 400)
    return HTTPResponse(
        'Create new submission',
        data={'submissionId': str(submission.id)},
    )


@comment_api.route('/<_id>', methods=['DELETE'])
@login_required
@Request.doc('_id', 'comment', Comment)
def delete_comment(
    user,
    comment: Comment,
):
    if not comment.permission(user=user, req={'d'}):
        return HTTPError('Permission denied', 403)
    comment.delete()
    return HTTPResponse('success')


@comment_api.route('<_id>/like', methods=['GET'])
@login_required
@Request.doc('_id', 'comment', Comment)
def like_comment(user, comment: Comment):
    comment.like(user=user)
    return HTTPResponse('success')


@comment_api.route('/<_id>/rejudge', methods=['GET'])
@login_required
@Request.doc('_id', 'comment', Comment)
def rejudge(user, comment: Comment):
    if comment.depth != 0:
        return HTTPError('Not a submission', 400)
    if not comment.permission(user=user, req={'j'}):
        return HTTPError('Forbidden', 403)
    try:
        comment.submit()
    except SubmissionPending as e:
        return HTTPError(str(e), 503)
    return HTTPResponse('success')
