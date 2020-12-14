from flask import Blueprint, request
from urllib import parse
import threading

from mongo import *
from mongo import engine, attachment
from .auth import *
from .course import *
from .utils import *
__all__ = ['attachment_api']

attachment_api = Blueprint('attachment_api', __name__)


@attachment_api.route('/', methods=['GET'])
@Request.json('filename')
@login_required
def get_attachment_list(user, filename):
    if filename is None:
        return HTTPResponse(
            'get all attachments\' names',
            data=[a.file.filename for a in engine.Attachment.objects])
    else:
        attachment = Attachment(filename)
        if not attachment:
            return HTTPError('file not found', 404)

        return send_file(
            attachment,
            as_attachment=True,
            cache_timeout=30,
            attachment_filename=attachment.filename,
        )


@attachment_api.route('/', methods=['POST'])
@Request.files('file_obj')
@Request.form('filename')
@Request.form('description')
@login_required
@identity_verify(0, 1)
def add_attachment(
    user,
    file_obj,
    filename,
    description,
):
    '''
    add an attachment to db
    '''
    try:
        Attachment.add(file_obj,
                       filename=filename,
                       description=description)
    except FileExistsError as e:
        return HTTPError(str(e), 400)
    return HTTPResponse('success')


@attachment_api.route('/<filename>', methods=['PUT', 'DELETE'])
@Request.files('file_obj')
@Request.form('filename')
@Request.form('description')
@login_required
@identity_verify(0, 1)
def patch_attachment(
    user,
    file_obj,
    filename,
    description,
):
    '''
    update or delete an attachment
    '''
    atta = Attachment(filename)
    if request.method == 'PUT':
        try:
            atta.update(file_obj, filename, description)
        except FileNotFoundError as e:
            return HTTPError(str(e), 400)
    elif request.method == 'DELETE':
        try:
            atta.delete()
        except FileNotFoundError as e:
            return HTTPError(str(e), 400)
    return HTTPResponse('success')
