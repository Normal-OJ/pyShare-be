from flask import Blueprint, request, send_file

from mongo import *
from mongo import engine
from .auth import *
from .course import *
from .utils import *
__all__ = ['attachment_api']

attachment_api = Blueprint('attachment_api', __name__)


@attachment_api.route('/<filename>', methods=['GET'])
@login_required
@Request.doc('filename', 'attachment', Attachment)
def get_attachment(user, attachment):
    return send_file(
        attachment.file,
        as_attachment=True,
        cache_timeout=30,
        attachment_filename=attachment.filename,
    )


@attachment_api.route('/', methods=['GET'])
@login_required
def get_attachment_list(user):
    return HTTPResponse('get all attachments\' names',
                        data=[{
                            'filename': a.filename,
                            'description': a.description
                        } for a in engine.Attachment.objects])


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
        Attachment.add(file_obj, filename=filename, description=description)
    except FileExistsError as e:
        return HTTPError(str(e), 400)
    except FileNotFoundError as e:
        return HTTPError(str(e), 404)
    except ValidationError as ve:
        return HTTPError(str(ve), 400, data=ve.to_dict())
    return HTTPResponse('success')


@attachment_api.route('/<filename>', methods=['PUT'])
@Request.files('file_obj')
@Request.form('description')
@login_required
@identity_verify(0, 1)
@Request.doc('filename', 'atta', Attachment)
def edit_attachment(
    user,
    file_obj,
    description,
    atta,
):
    '''
    update an attachment
    '''
    try:
        atta.update(file_obj, description)
    except ValidationError as ve:
        return HTTPError(str(ve), 400, data=ve.to_dict())
    return HTTPResponse('success')


@attachment_api.route('/<filename>', methods=['DELETE'])
@login_required
@identity_verify(0, 1)
@Request.doc('filename', 'atta', Attachment)
def delete_attachment(
    user,
    atta,
):
    '''
    delete an attachment
    '''
    atta.delete()
    return HTTPResponse('success')
