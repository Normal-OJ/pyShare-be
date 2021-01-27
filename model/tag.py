from flask import Blueprint, request
from urllib import parse
import threading

from mongo import *
from mongo import engine
from .auth import *
from .course import *
from .utils import *
__all__ = ['tag_api']

tag_api = Blueprint('tag_api', __name__)


@tag_api.route('/', methods=['GET'])
@Request.args('course')
@login_required
def get_tag_list(user, course):
    c = Course(course)
    if course is None or c is None:
        return HTTPResponse('get all tags',
                            data=[t.value for t in engine.Tag.objects])
    else:
        return HTTPResponse(f'get {c}\'s tags', data=c.tags)


@tag_api.route('/', methods=['POST', 'DELETE'])
@Request.json('tags')
@login_required
@identity_verify(0, 1)
def manage_tag(user, tags):
    success = []
    fail = []
    for tag in tags:
        try:
            if request.method == 'POST':
                Tag.add(value=tag)
            else:
                Tag(tag).delete()
        except (engine.DoesNotExist, engine.ValidationError,
                engine.NotUniqueError) as e:
            fail.append({
                'value': tag,
                'msg': str(e),
            })
        else:
            success.append(tag)
    if len(fail) != 0:
        return HTTPError(
            'Exist some tags fail',
            400,
            data={
                'fail': fail,
                'success': success,
            },
        )
    return HTTPResponse('success')
