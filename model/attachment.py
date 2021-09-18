from flask import Blueprint, request, send_file

from mongo import *
from mongo import engine
from .auth import *
from .course import *
from .utils import *

__all__ = ['attachment_api']

attachment_api = Blueprint('attachment_api', __name__)


@attachment_api.route('/<id>', methods=['GET'])
@login_required
@Request.doc('id', 'attachment', Attachment)
def get_attachment(user, attachment):
    attachment.obj.update(inc__download_count=1)
    return send_file(
        attachment.file,
        as_attachment=True,
        max_age=30,
        download_name=attachment.filename,
    )


@attachment_api.route('/<id>/meta', methods=['GET'])
@login_required
@Request.doc('id', 'attachment', Attachment)
def get_an_attachment(user, attachment):
    return HTTPResponse(
        'get an attachment',
        data=attachment.to_dict(),
    )


@attachment_api.route('/', methods=['GET'])
@login_required
def get_attachment_list(user):
    return HTTPResponse(
        'get all attachments\' names',
        data=[a.to_dict() for a in engine.Attachment.objects],
    )


@attachment_api.route('/', methods=['POST'])
@Request.files('file_obj')
@Request.form('filename', 'description', 'patch_note', 'tags')
@identity_verify(0, 1)
def add_attachment(
    user,
    file_obj,
    filename,
    description,
    patch_note,
    tags,
):
    '''
    add an attachment to db
    '''
    try:
        atta = Attachment.add(
            author=user,
            file_obj=file_obj,
            filename=filename,
            description=description,
            patch_note=patch_note,
            tags_str=tags,
        )
    except FileExistsError as e:
        return HTTPError(e, 400)
    except PermissionError as e:
        return HTTPError(e, 403)
    except (FileNotFoundError, engine.DoesNotExist) as e:
        return HTTPError(e, 404)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())
    return HTTPResponse('success', data={'id': atta.id})


@attachment_api.route('/<id>', methods=['PUT'])
@Request.files('file_obj')
@Request.form('description', 'patch_note', 'tags', 'filename')
@identity_verify(0, 1)
@Request.doc('id', 'atta', Attachment)
def edit_attachment(
    user,
    file_obj,
    description,
    patch_note,
    tags,
    filename,
    atta,
):
    '''
    update an attachment
    '''
    if not atta.permission(user=user, req={'w'}):
        return HTTPError('Permission denied.', 403)
    try:
        with get_redis_client().lock(f'{atta}'):
            atta.update(filename, file_obj, description, patch_note, tags)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())
    except engine.DoesNotExist as e:
        return HTTPError(e, 404)
    return HTTPResponse('success')


@attachment_api.route('/<id>', methods=['DELETE'])
@identity_verify(0, 1)
@Request.doc('id', 'atta', Attachment)
def delete_attachment(
    user,
    atta,
):
    '''
    delete an attachment
    '''
    if not atta.permission(user=user, req={'w'}):
        return HTTPError('Permission denied.', 403)
    atta.delete()
    return HTTPResponse('success')
