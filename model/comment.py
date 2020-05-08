from flask import Blueprint
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
        except engine.DoesNotExist:
            return HTTPError('Can not find some docuemnt', 404)
    else:
        return HTTPError('Unknown target', 400)
    return HTTPResponse('success', data={'id': str(comment.id)})


@comment_api.route('/<_id>', methods=['GET'])
@login_required
@Request.doc('_id', 'comment', Comment)
def get_comment(user, comment: Comment):
    if comment.permission(user=user, req={'r'}):
        return HTTPError('permission denied', 403)
    return HTTPResponse('success', data=comment.to_dict())


@comment_api.route('/<_id>/file/<name>', methods=['GET'])
@login_required
@Request.doc('_id', 'comment', Comment)
def get_comment_file(user, comment: Comment):
    try:
        f = comment.get_file(name)
        return send_file(
            f,
            as_attachment=True,
            cache_timeout=30,
            attachment_filename=f.filename,
        )
    except FileNotFoundError:
        return HTTPError('file not found', 404)
    except NotAComment:
        return HTTPError('not a comment', 400)


@comment_api.route('/<_id>', methods=['PUT'])
@Request.json(
    'content: str',
    'title: str',
    'code',
)
@Request.doc('_id', 'comment', Comment)
@login_required
def modify_comment(
    user,
    comment: Comment,
    content,
    title,
    code,
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
        # if it's a direct comment and need to rejudge
        if comment.depth == 0 and code and code != comment.submission.code:
            # update code & rejudge
            comment.submission.update(code=code)
            comment.submit()
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