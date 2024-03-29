from flask import Blueprint
from typing import Optional
from mongo import *
from mongo import engine
from .auth import *
from .notifier import *
from .utils import *

__all__ = ['sandbox_api']

sandbox_api = Blueprint('sandbox_api', __name__)


@sandbox_api.before_request
@login_required
@identity_verify(User.engine.Role.ADMIN)
def before_sandbox_api(user):
    '''
    Only admin can use this route
    '''


@sandbox_api.errorhandler(ValidationError)
def on_validation_error(_: ValidationError):
    return HTTPError('Invalid sandbox data', 400)


@sandbox_api.errorhandler(engine.Sandbox.DoesNotExist)
def on_does_not_exist(_):
    return HTTPError('Sandbox not found', 404)


@sandbox_api.get('/')
def get_all():
    return HTTPResponse(data=[sb.to_json() for sb in engine.Sandbox.objects])


@sandbox_api.post('/')
@Request.json(
    'url: str',
    'token: str',
    'alias',
)
def add_one(
    url: str,
    token: str,
    alias: Optional[str],
):
    try:
        engine.Sandbox(
            url=url,
            token=token,
            alias=alias,
        ).save(force_insert=True)
    except NotUniqueError:
        return HTTPError('Duplicated url', 422)
    return HTTPResponse()


@sandbox_api.put('/')
@Request.json(
    'url: str',
    'alias',
)
def update_one(
    url: str,
    alias: Optional[str],
):
    sandbox = engine.Sandbox.objects(url=url).get()
    sandbox.update(alias=alias)
    return HTTPResponse()


@sandbox_api.delete('/')
@Request.json('url: str')
def delete_one(url: str):
    sandbox = engine.Sandbox.objects(url=url).get()
    sandbox.delete()
    return HTTPResponse()
