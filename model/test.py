from flask import Blueprint

from .auth import *
from .utils import *

__all__ = ['test_api']

test_api = Blueprint('test_api', __name__)


@test_api.route('/')
@login_required
def test(user):
    return HTTPResponse(user.username)
