from flask import Blueprint

from mongo import *
from mongo import engine
from .utils import *
from .auth import *

__all__ = ['requirement_api']

requirement_api = Blueprint('requirement_api', __name__)


@requirement_api.get('/<_id>')
@Request.doc('_id', 'req', Requirement)
@login_required
def get_requirement(user, req):
    if not Course(req.task.course).permission(
            user=user,
            req=Course.Permission.READ,
    ):
        return HTTPError('Permission denied', 403)
    data = req.to_mongo().to_dict()
    data['progress'] = req.progress(user)
    return HTTPResponse(data=data)
