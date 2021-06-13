from flask import Blueprint
from mongo import *
from mongo import engine
from .auth import login_required
from .utils import *

__all__ = ('school_api', )

school_api = Blueprint('school_api', __name__)


@school_api.before_request
@login_required
def before_school_api(user: User):
    '''
    Ensure only admin can call this
    '''
    if user < 'admin':
        return HTTPError('Only admin can call this api.', 403)


@school_api.route('/', methods=['GET'])
def get_all():
    return HTTPReseponse(data=[s.to_dict() for s in engine.School.objects])


@school_api.route('/<abbr>', methods=['GET'])
def get_single(abbr: str):
    try:
        s = engine.School.objects.get(id=abbr)
    except DoesNotExist:
        return HTTPError('School not found.', 404)
    return HTTPResponse(data=s.to_dict())


@school_api.route('/', methods=['POST'])
@Request.json(
    'abbr: str',
    'name: str',
)
def add_school(
    abbr: str,
    name: str,
):
    s = engine.School(
        abbr=abbr,
        name=name,
    )
    try:
        s.save()
    except ValidationError as ve:
        return HTTPError(
            'Invalid data.',
            400,
            data=ve.to_dict(),
        )
    except NotUniqueError:
        return HTTPError(
            f'{abbr} has been used.',
            400,
        )
    return HTTPResponse(data=s.to_dict())
