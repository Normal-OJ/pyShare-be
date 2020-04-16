from flask import Blueprint
from .utils import *
from .auth import *
from mongo import *
from mongo import engine

__all__ = ['comment_api']

comment_api = Blueprint('comment_api', __name__)


@comment_api.route('/', methods=['POST'])
@login_required
@Request.json(
    'target: str',
    'id_: str',
    'title: str',
    'content: str',
    'code: str',
)
def create_comment(user, target, code, id_, **ks):
    if target == 'comment':
        try:
            comment = Comment.add_to_comment(
                target=id_,
                **ks,
            )
        except engine.DoesNotExist:
            return HTTPError('Can not find some docuemnt', 404)
    elif target == 'problem':
        try:
            comment = Comment.add_to_comment(
                target=id_,
                code=code,
                **ks,
            )
        except engine.DoesNotExist:
            return HTTPError('Can not find some docuemnt', 404)
    else:
        return HTTPError('Unknown target', 400)
    return HTTPResponse('success', data={'id': comment.id})


@comment_api.route('/<_id>', methods=['GET'])
@login_required
@Request.doc('_id', 'comment', Comment)
def get_comment(user, comment: Comment):
    data = comment.to_mongo()
    author = User(data['author'])
    data['author'] = {
        'username': author.username,
        'displayName': author.displayName,
    }
    return HTTPResponse('success', data=data)


@comment_api.route('/<_id>', methods=['PUT'])
@login_required
@Request.json('content: str', 'code: str')
@Request.doc('_id', 'comment', Comment)
def modify_comment(
    user,
    comment: Comment,
    content,
    code,
):
    if not comment.permission(user, {'w'}):
        return HTTPError('Permission denied.', 403)
    try:
        # update content
        comment.update(content=content)
        # update code & rejudge
    except engine.ValidationError as ve:
        return HTTPError(
            'Invalid data',
            400,
            data=ve.to_dict(),
        )
    return HTTPResponse('success')


@comment_api.route('/<_id>', methods=['DELETE'])
@login_required
@Request.doc('_id', 'comment', Comment)
def delete_comment(
    user,
    comment: Comment,
):
    if not comment.permission(user, {'d'}):
        return HTTPError('Permission denied', 403)
    comment.delete()
    return HTTPResponse('success')


@comment_api.route('<_id>/like', methods=['GET'])
@login_required
@Request.doc('_id', 'comment', Comment)
def like_comment(user, comment: Comment):
    comment.like(user)
    return HTTPResponse('success')


@comment_api.route('/<_id>/rejudge', methods=['GET'])
@login_required
@Request.doc('_id', 'comment', Comment)
def rejudge(user, comment: Comment):
    if comment.depth != 0:
        return HTTPError('Not a submission', 400)
    if not comment.permission({'j'}):
        return HTTPError('Forbidden', 403)
    try:
        comment.submission.submit()
    except SubmissionPending as e:
        return HTTPError(str(e), 503)
    return HTTPResponse('success')