from flask import Blueprint, request, send_file
from urllib import parse
import threading

from mongo import *
from mongo import engine
from .auth import *
from .notifier import *
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
    'is_template',
    'allow_multiple_comments',
)
@login_required
def get_problem_list(
    user,
    tags,
    offset,
    count,
    is_template,
    allow_multiple_comments,
    **ks,
):
    # filter values user passed and decode
    ks = {k: parse.unquote(v) for k, v in ks.items() if v is not None}
    # change key name from 'title' to 'name'
    if 'title' in ks:
        ks['name'] = ks.pop('title')
    tags = parse.unquote(tags).split(',') if tags else None
    # parse offset & count
    try:
        if offset is not None:
            ks['offset'] = int(offset)
        if count is not None:
            ks['count'] = int(count)
    except TypeError:
        return HTTPError('count and offset only accept integer', 400)
    try:
        if is_template is not None:
            ks['is_template'] = to_bool(is_template)
        if allow_multiple_comments is not None:
            ks['allow_multiple_comments'] = to_bool(allow_multiple_comments)
    except TypeError:
        return HTTPError(
            'isTemplate and allowMultipleComments only accept boolean', 400)
    ps = Problem.filter(
        tags=tags,
        only=['pid'],
        **ks,
    )
    # check whether user has read permission
    ps = [Problem(p.pid) for p in ps]
    ps = [p.to_dict() for p in ps if p.permission(
        user=user,
        req={'r'},
    )]
    return HTTPResponse('here you are, bro', data=ps)


@problem_api.route('/<int:pid>', methods=['GET'])
@login_required
@Request.doc('pid', 'problem', Problem)
def get_single_problem(user, problem):
    if not problem.permission(user=user, req={'r'}):
        return HTTPError('Not enough permission', 403)
    return HTTPResponse(
        'here you are, bro',
        data=problem.to_dict(),
    )


@problem_api.route('/', methods=['POST'])
@Request.json(
    'title: str',
    'description: str',
    'tags: list',
    'course: str',
    'default_code: str',
    'status: int',
    'is_template: bool',
    'allow_multiple_comments: bool',
)
@Request.doc('course', 'course', Course)
@login_required
@fe_update('PROBLEM', 'course')
def create_problem(
        user,
        **p_ks,  # problem args
):
    '''
    create a new problem
    '''
    try:
        # filter None
        p_ks = {k: v for k, v in p_ks.items() if v is not None}
        problem = Problem.add(
            author=user.pk,
            **p_ks,
        )
    except engine.ValidationError as ve:
        return HTTPError(str(ve), 400, data=ve.to_dict())
    except TagNotFoundError as e:
        return HTTPError(str(e), 404)
    except PermissionError as e:
        return HTTPError(str(e), 403)
    return HTTPResponse(
        'success',
        data={
            'course': p_ks['course'].name,
            'pid': problem.pid,
        },
    )


@problem_api.route('/<int:pid>', methods=['PUT'])
@Request.json(
    'title: str',
    'description: str',
    'tags: list',
    'default_code: str',
    'status: int',
    'is_template: bool',
    'allow_multiple_comments: bool',
)
@Request.doc('pid', 'problem', Problem)
@login_required
@fe_update('PROBLEM', 'course')
def modify_problem(
    user,
    problem,
    tags,
    **p_ks,
):
    if not problem.permission(user=user, req={'w'}):
        return HTTPError('Permission denied.', 403)
    # if allow_multiple_comments is False
    if user < 'teacher' and p_ks.get('allow_multiple_comments') == False:
        return HTTPError('Students have to allow multiple comments.', 403)
    for tag in tags:
        c = Course(problem.course.name)
        if not c.check_tag(tag):
            return HTTPError(
                'Exist tag that is not allowed to use in this course', 400)
    try:
        p_ks = {k: v for k, v in p_ks.items() if v is not None}
        problem.update(**p_ks, tags=tags)
    except engine.ValidationError as ve:
        return HTTPError(
            'Invalid data',
            400,
            data=ve.to_dict(),
        )
    return HTTPResponse(
        'success',
        data={'course': problem.course.name},
    )


@problem_api.route('/<int:pid>', methods=['DELETE'])
@Request.doc('pid', 'problem', Problem)
@login_required
@fe_update('PROBLEM', 'course')
def delete_problem(user, problem):
    '''
    delete a problem
    '''
    # student can delete only self problem
    if not problem.permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    course = problem.course.name
    problem.delete()
    return HTTPResponse(
        f'{problem} deleted.',
        data={'course': course},
    )


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
    if not problem.permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    if attachment_name is None:
        return HTTPError('you need an attachment name', 400)
    if request.method == 'POST':
        use_db = False
        try:
            # use public attachment db
            if attachment is None:
                attachment = Attachment(attachment_name).copy()
                use_db = True
            problem.insert_attachment(
                attachment,
                filename=attachment_name,
            )
        except FileExistsError as e:
            return HTTPError(str(e), 400)
        except FileNotFoundError as e:
            return HTTPError(str(e), 404)
        return HTTPResponse(
            f'successfully update from {"db file" if use_db else "your file"}')
    elif request.method == 'DELETE':
        try:
            problem.remove_attachment(attachment_name)
        except FileNotFoundError as e:
            return HTTPError(str(e), 404)
        return HTTPResponse('successfully delete')


@problem_api.route('/<int:pid>/attachment/<name>', methods=['GET'])
@login_required
@Request.doc('pid', 'problem', Problem)
def get_attachment(user, problem, name):
    if not problem.permission(user=user, req={'r'}):
        return HTTPError('Permission denied.', 403)
    name = parse.unquote(name)
    for att in problem.attachments:
        if att.filename == name:
            return send_file(
                att,
                as_attachment=True,
                cache_timeout=30,
                attachment_filename=att.filename,
            )
    return HTTPError('file not found', 404)


@problem_api.route('/<int:pid>/clone/<course_name>', methods=['GET'])
@Request.doc('pid', 'problem', Problem)
@Request.doc('course_name', 'course', Course)
@fe_update('PROBLEM', 'course')
def clone_problem(user, problem, course):
    '''
    clone a problem to another course
    '''
    if not problem.permission(user=user, req={'r'}):
        return HTTPError('Permission denied.', 403)
    try:
        problem.copy(target_course=course)
    except engine.ValidationError as ve:
        return HTTPError(str(ve), 400, data=ve.to_dict())
    except PermissionError as e:
        return HTTPError(str(e), 403)
    return HTTPResponse(
        'Success.',
        data={'course': course.name},
    )
