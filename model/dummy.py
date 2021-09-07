from flask import Blueprint
from mongo import *
from tests import utils
from .utils import *
from .auth import identity_verify

__all__ = ['dummy_api']

dummy_api = Blueprint('dummy_api', __name__)


@dummy_api.before_request
@identity_verify(User.engine.Role.ADMIN)
def before_dummy_api():
    '''
    Only admin can call this
    '''


@dummy_api.get('/')
def health_check():
    return HTTPResponse()


@dummy_api.post('/user')
@Request.json(
    'username: str',
    'password: str',
    'email: str',
    'has_email: bool',
    'role: int',
)
def create_user(**ks):
    u = utils.user.lazy_signup(**ks)
    return HTTPResponse(data=u.info)
