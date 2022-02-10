from sre_constants import CATEGORY_SPACE
from flask import Blueprint, request

from mongo import *
from mongo import engine
from .auth import *
from .course import *
from .utils import *

__all__ = ['tag_api']

tag_api = Blueprint('tag_api', __name__)


@tag_api.route('/', methods=['GET'])
@Request.args('course', 'category')
@login_required
def get_tag_list(user, course, category):
    if category is None:
        category = Tag.engine.Category.NORMAL_PROBLEM
    else:
        try:
            category = int(category)
        except ValueError:
            return HTTPError(
                'Invalid category. It should be an integer',
                400,
            )
    tags = Tag.filter(
        course=course,
        category=category,
    )
    return HTTPResponse(data=tags)


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
