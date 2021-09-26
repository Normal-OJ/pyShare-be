from flask import Blueprint
from mongo import *
from tests import utils
from .utils import *
from .auth import identity_verify

__all__ = ['dummy_api']

dummy_api = Blueprint('dummy_api', __name__)


@dummy_api.before_request
@identity_verify(User.engine.Role.ADMIN)
def before_dummy_api(user):
    '''
    Only admin can call this
    '''


@dummy_api.get('/')
def health_check():
    return HTTPResponse()


@dummy_api.post('/user')
@Request.json(
    'username',
    'password',
    'email',
    'has_email',
    'role',
)
def create_user(**ks):
    u = utils.user.lazy_signup(**drop_none(ks))
    return HTTPResponse(data=u.info)


@dummy_api.post('/comment')
@Request.json(
    'title',
    'content',
    'author',
    'problem',
    'code',
)
def create_comment(**ks):
    c = utils.comment.lazy_add_comment(**ks)
    return HTTPResponse(data=c.to_dict())


@dummy_api.post('/reply')
@Request.json(
    'comment',
    'author',
    'title',
    'content',
)
def create_reply(**ks):
    r = utils.comment.lazy_add_reply(**ks)
    return HTTPResponse(data=r.to_dict())


@dummy_api.post('/course')
@Request.json(
    'name',
    'teacher',
    'year',
    'semester',
    'status',
    'tags',
)
def create_course(**ks):
    c = utils.course.lazy_add(**ks)
    return HTTPResponse(data={'id': c.id})


@dummy_api.post('/problem')
@Request.json(
    'author',
    'course',
    'is_oj',
    'input',
    'output',
    'title',
    'description',
    'default_code',
    'tags',
    'status',
    'is_template',
    'allow_multiple_comments',
)
def create_problem(**ks):
    p = utils.problem.lazy_add(**drop_none(ks))
    return HTTPResponse(data=p.to_dict())
