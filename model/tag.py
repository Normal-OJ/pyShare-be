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
    c = Course(course) if course else None
    if c is None:
        return HTTPResponse('get all tags',
                            data=[t.value for t in engine.Tag.objects])
    else:
        return HTTPResponse(f'get {c}\'s tags', data=c.tags)


@tag_api.route('/', methods=['POST', 'DELETE'])
@Request.json('tags', 'category')
@identity_verify(0, 1)
def manage_tag(user, tags, category):
    success = []
    fail = []
    for tag in tags:
        try:
            if request.method == 'POST':
                Tag.add(value=tag, category=category)
            else:
                Tag(tag).delete(category)
        except (engine.DoesNotExist, engine.ValidationError,
                engine.NotUniqueError, PermissionError, ValueError) as e:
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


@tag_api.route('/check', methods=['POST'])
@Request.json('tags', 'category')
@identity_verify(0, 1)
def check_tag_is_used(user, tags, category):
    result = {t: Tag(t).is_used(category) for t in tags}
    return HTTPResponse('Checked whether the tags are used', data=result)
