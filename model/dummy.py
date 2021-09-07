from flask import Blueprint
from typing import Dict
from mongo import *
from tests import utils
from .utils import *
from .auth import identity_verify

__all__ = ['dummy_api']


def drop_none(d: Dict):
    return {k: v for k, v in d.items() if v is not None}


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
