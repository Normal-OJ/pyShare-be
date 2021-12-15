from flask import Blueprint, request
from urllib import parse
import threading

from mongo import *
from mongo import engine
from .auth import *
from .course import *
from .utils import *

__all__ = ['task_api']

task_api = Blueprint('task_api', __name__)


@task_api.route('/', methods=['GET'])
@Request.json(
    'course: str', )
@Request.doc('course', Course)
@login_required
def get_task_list(user, course):
    tasks = engine.Tag.object(course=course.obj)
    return HTTPResponse(f'get {course}\'s tags', data=tasks)


@task_api.route('/', methods=['POST'])
@Request.json('course: str', 'starts_at', 'ends_at')
@Request.doc('course', Course)
@identity_verify(0, 1)
def add_task(user, course, starts_at, ends_at):
    try:
        task = Task.add(
            course=course,
            starts_at=starts_at,
            ends_at=ends_at,
        )
    except engine.ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())
    return HTTPResponse(
        'success',
        data={
            'id': task.id,
        },
    )


@task_api.route('/<_id>', methods=['GET'])
@Request.doc('_id', 'task', Task)
@login_required
def get_task(user, task):
    return HTTPResponse(f'success', data=task)
