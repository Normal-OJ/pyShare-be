from flask import Blueprint, request

from mongo import *
from mongo import engine
from .utils import *
from .auth import *

__all__ = ['requirement_api']

requirement_api = Blueprint('requirement_api', __name__)


@requirement_api.route('/<_id>', methods=['GET'])
@login_required
def get_requirement(user, _id):
    try:
        return HTTPResponse(f'success',
                            data=Requirement(_id).to_mongo().to_dict())
    except engine.DoesNotExist as e:
        return HTTPError(e, 400)
    except engine.ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())
