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
    'course',
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
@login_required
@Request.doc('pid', 'problem', Problem)
def get_single_problem(user, problem):
    p = problem.to_mongo()
    p['author'] = User(p['author']).info
    if not user > 'student':
        del p['status']
    return HTTPResponse('here you are, bro', data=p)


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
    except (engine.ValidationError, TagNotFoundError) as ve:
        return HTTPError(str(ve), 400, data=ve.to_dict())
    except PermissionError as e:
        return HTTPError(str(e), 403)
    return HTTPResponse(
        'success',
        data={'pid': problem.pid},
    )


@problem_api.route('/<int:pid>', methods=['PUT'])
@Request.json(
    'title: str',
    'description: str',
    'tags: list',
    'default_code: str',
    'status: int',
)
@Request.doc('pid', 'problem', Problem)
@login_required
def modify_problem(
    user,
    problem,
    title,
    description,
    tags,
    default_code,
    status,
):
    if not problem.permission(user, {'w'}):
        return HTTPError('Permission denied.', 403)
    for tag in tags:
        if not course.check_tag(tag):
            return HTTPError(
                'Exist tag that is not allowed to use in this course', 400)
    try:
        problem.update(
            title=title,
            description=description,
            tags=tags,
            default_code=default_code,
            status=status,
        )
    except engine.ValidationError as ve:
        return HTTPError(
            'Invalid data',
            400,
            data=ve.to_dict(),
        )
    return HTTPResponse('success')


@problem_api.route('/<int:pid>', methods=['DELETE'])
@Request.doc('pid', 'problem', Problem)
@login_required
def delete_problem(user, problem):
    '''
    delete a problem
    '''
    # student can delete only self problem
    if not problem.permission(user, {'w'}):
        return HTTPError('Not enough permission', 403)
    problem.delete()
    return HTTPResponse(f'{problem} deleted.')


@problem_api.route('/<int:pid>/attachment', methods=['POST', 'DELETE'])
@Request.doc('pid', 'problem', Problem)
@Request.files('attachment')
@Request.form('attachment_name')
@login_required
def patch_attachment(
    user,
    problem,
    attachment,
    attachment_name,
):
    '''
    update the problem's attachment
    '''
    if not problem.permission(user, {'w'}):
        return HTTPError('Not enough permission', 403)
    if request.method == 'POST':
        try:
            problem.insert_attachment(
                filename=attachment.filename,
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
