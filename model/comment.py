from flask import Blueprint
from .utils import *
from .auth import *
from .notifier import *
from mongo import *
from mongo import engine
from datetime import datetime

__all__ = ['comment_api']

comment_api = Blueprint('comment_api', __name__)


@comment_api.post('/')
@login_required
@Request.json(
    'target: str',
    'id_',
    'title: str',
    'content: str',
    'code: str',
)
@fe_update('COMMENT', 'target', 'target_id')
def create_comment(user, target, code, id_, **ks):
    if target == 'comment':
        try:
            comment = Comment.add_to_comment(
                target=id_,
                author=user,
                **ks,
            )
        except engine.DoesNotExist:
            return HTTPError('Can not find some docuemnt', 404)
        except PermissionError as e:
            return HTTPError(e, 403)
    elif target == 'problem':
        try:
            comment = Comment.add_to_problem(
                target=id_,
                code=code,
                author=user,
                **ks,
            )
        except TooManyComments:
            return HTTPError('You can only have one comment', 400)
        except engine.DoesNotExist:
            return HTTPError('Can not find some docuemnt', 404)
        except PermissionError as e:
            return HTTPError(e, 403)
    else:
        return HTTPError('Unknown target', 400)
    return HTTPResponse(
        'success',
        data={
            'id': comment.id,
            'target': target,
            'target_id': id_,
        },
    )


@comment_api.get('/<_id>')
@login_required
@Request.doc('_id', 'comment', Comment)
def get_comment(user, comment: Comment):
    if not comment.permission(user=user, req=Comment.Permission.READ):
        return HTTPError('permission denied', 403)
    return HTTPResponse('success', data=comment.to_dict())


@comment_api.get('/<_id>/permission')
@login_required
@Request.doc('_id', 'comment', Comment)
def get_comment_permission(user, comment: Comment):
    return HTTPResponse(data=comment.own_permission(user=user).value)


@comment_api.put('/<_id>')
@Request.json(
    'content: str',
    'title: str',
)
@Request.doc('_id', 'comment', Comment)
@login_required
@fe_update('COMMENT', 'target', 'target_id')
def modify_comment(
    user,
    comment: Comment,
    content,
    title,
):
    if not comment.permission(user=user, req=Comment.Permission.WRITE):
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
    return HTTPResponse(
        'success',
        data={
            'target':
            'comment',
            'target_id':
            engine.Comment.objects.get(
                depth=0,
                floor=comment.floor,
                problem=comment.problem.pid,
            ).id,
        } if comment.depth else {
            'target': 'problem',
            'target_id': comment.problem.pid,
        },
    )


@comment_api.post('/<_id>/submission')
@login_required
@Request.json('code: str')
@Request.doc('_id', 'comment', Comment)
def create_new_submission(user, code, comment: Comment):
    if not comment.permission(user=user, req=Comment.Permission.REJUDGE):
        return HTTPError('Permission denied.', 403)
    try:
        submission = comment.add_new_submission(code)
    except NotAComment:
        return HTTPError('Only comments can has code.', 400)
    except engine.ValidationError as ve:
        return HTTPError('The source code is invalid!', 400)
    return HTTPResponse(
        'Create new submission',
        data={'submissionId': submission.id},
    )


@comment_api.delete('/<_id>')
@login_required
@Request.doc('_id', 'comment', Comment)
@fe_update('COMMENT', 'target', 'target_id')
def delete_comment(
    user,
    comment: Comment,
):
    if not comment.permission(user=user, req=Comment.Permission.DELETE):
        return HTTPError('Permission denied', 403)
    comment.delete()
    return HTTPResponse(
        'success',
        data={
            'target':
            'comment',
            'target_id':
            engine.Comment.objects.get(
                depth=0,
                floor=comment.floor,
                problem=comment.problem.pid,
            ).id,
        } if comment.depth else {
            'target': 'problem',
            'target_id': comment.problem.pid,
        },
    )


@comment_api.get('<_id>/like')
@login_required
@Request.doc('_id', 'comment', Comment)
def like_comment(user, comment: Comment):
    if not comment.permission(user=user, req=Comment.Permission.READ):
        return HTTPError('Permission denied', 403)
    comment.like(user=user)
    return HTTPResponse('success')


@comment_api.post('/<_id>/rejudge')
@login_required
@Request.doc('_id', 'comment', Comment)
def rejudge(user, comment: Comment):
    if not comment.is_comment:
        return HTTPError('Not a submission', 400)
    if not comment.permission(user=user, req=Comment.Permission.REJUDGE):
        return HTTPError('Forbidden', 403)
    try:
        comment.submit()
    except Submission.Pending as e:
        return HTTPError(e, 503)
    return HTTPResponse('success')
