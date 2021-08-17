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
    return send_file(
        attachment.file,
        as_attachment=True,
        cache_timeout=30,
        attachment_filename=attachment.filename,
    )


@attachment_api.route('/<id>/meta', methods=['GET'])
@login_required
@Request.doc('id', 'attachment', Attachment)
def get_an_attachment(user, attachment):
    return HTTPResponse(
        'get an attachment',
        data={
            'filename': attachment.filename,
            'description': attachment.description,
            'author': attachment.author.info,
            'created': attachment.created.timestamp(),
            'updated': attachment.updated.timestamp(),
            'id': attachment.id,
            'size': attachment.size,
            'patchNotes': attachment.patch_notes,
            'tags': attachment.tags,
        },
    )


@attachment_api.route('/', methods=['GET'])
@login_required
def get_attachment_list(user):
    return HTTPResponse(
        'get all attachments\' names',
        data=[{
            'filename': a.filename,
            'description': a.description,
            'author': a.author.info,
            'created': a.created.timestamp(),
            'updated': a.updated.timestamp(),
            'id': a.id,
            'size': a.size,
            'patchNotes': a.patch_notes,
            'tags': a.tags,
        } for a in engine.Attachment.objects],
    )


@attachment_api.route('/', methods=['POST'])
@Request.files('file_obj')
@Request.form('filename')
@Request.form('description')
@Request.form('patch_note')
@Request.form('tags')
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
    except (FileNotFoundError, engine.DoesNotExist) as e:
        return HTTPError(e, 404)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())
    return HTTPResponse('success', data={'id': atta.id})


@attachment_api.route('/<id>', methods=['PUT'])
@Request.files('file_obj')
@Request.form('description')
@Request.form('patch_note')
@Request.form('tags')
@Request.form('filename')
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
