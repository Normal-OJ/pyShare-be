from flask import Blueprint, request
from urllib import parse
import threading

from mongo import *
from mongo import engine
from .auth import *
from .course import *
from .utils import *
__all__ = ['attachment_api']

attachment_api = Blueprint('attachment_api', __name__)


@attachment_api.route('/', methods=['GET'])
@login_required
def get_attachment_list(user):
    return HTTPResponse('get all attachments',
                            data=[a.file.filename for a in engine.Attachment.objects])


@attachment_api.route('/', methods=['POST', 'DELETE'])
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
