from flask import Blueprint, request
from urllib import parse
import threading

from mongo import *
from mongo import engine
from .auth import *
from .utils import *

__all__ = ['problem_api']

problem_api = Blueprint('problem_api', __name__)


@problem_api.route('/', methods=['GET'])
@Request.args(
    'offset',
    'count',
    'title',
    'tags',
)
@login_required
def get_problem_list(user, tags, **ks):
    ks = {k: v for k, v in ks.items() if v is not None}
    tags = tags.split(',') if tags else []
    ps = Problem.filter(
        tags=tags,
        only=[
            'pid',
            'title',
            'timestamp',
            'author',
        ] + ['status'] if user > 'student' else [],
        **ks,
    )
    ps = [p.to_mongo() for p in ps]
    for p in ps:
        p['author'] = User(p['author']).info
    return HTTPResponse('here you are, bro', data=ps)


@problem_api.route('/<int:pid>', methods=['GET'])
def get_single_problem():
    pass


@problem_api.route('/', methods=['POST'])
@Request.json(
    'title: str',
    'description: str',
    'tags: list',
    'course: str',
    'default_code: str',
    'status: int',
)
@Request.doc('course', 'course', Course)
@login_required
@identity_verify(0, 1)
def create_problem(
    user,
    title,
    description,
    tags,
    course,
    default_code,
    status,
):
    '''
    create a new problem
    '''
    try:
        problem = Problem.add(
            title=title,
            description=description,
            tags=tags or [],
            course=course,
            author=user.username,
            default_code=default_code or '',
            status=status,
        )
    except engine.ValidationError as ve:
        return HTTPError(str(ve), 400, data=ve.to_dict())
    except PermissionError as e:
        return HTTPError(str(e), 403)
    return HTTPResponse(
        'success',
        data={'pid': problem.pid},
    )


@problem_api.route('/<int:pid>', methods=['DELETE'])
@Request.doc('pid', 'problem')
@login_required
@identity_verify(0, 1)
def delete_problem(user, problem):
    '''
    delete a problem
    '''
    problem.delete()
    return HTTPResponse(f'{problem} deleted.')


@problem_api.route('/<int:pid>/attachment', methods=['POST', 'DELETE'])
@Request.doc('pid', 'problem', Problem)
@Request.files('attachment')
@Request.form('attachment_name')
@login_required
@identity_verify(0, 1)
def patch_attachment(
    user,
    problem,
    attachment,
    attachment_name,
):
    '''
    update the problem's attachment
    '''
    if request.method == 'POST':
        try:
            problem.insert_attachment(
                name=attachment.filename,
                data=attachment.read(),
            )
        except FileExistsError as e:
            return HTTPError(str(e), 400)
    elif request.method == 'DELETE':
        try:
            problem.remove_attachment(attachment_name)
        except FileNotFoundError as e:
            return HTTPError(str(e), 400)
    return HTTPResponse('success')


@problem_api.route('/<int:pid>/clone/<course_name>', methods=['GET'])
@identity_verify(0, 1)
@Request.doc('pid', 'problem', Problem)
@Request.doc('course_name', 'course', Course)
def clone_problem(user, problem, course):
    '''
    clone a problem to another course
    '''
    try:
        problem.copy(course)
    except engine.ValidationError as ve:
        return HTTPError(str(ve), 400, data=ve.to_dict())
    except PermissionError as e:
        return HTTPError(str(e), 403)
    return HTTPResponse('Success.')
