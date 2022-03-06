from typing import Optional, List
from flask import Blueprint
from dateutil import parser

from mongo import *
from mongo import engine, requirement
from .course import *
from .utils import *
from .auth import *

__all__ = ['task_api']

task_api = Blueprint('task_api', __name__)


@course_api.get('/<course>/tasks')
@Request.doc('course', Course)
@login_required
def get_task_list(user: User, course: Course):
    if not course.permission(user=user, req=Course.Permission.READ):
        return HTTPError('Permission denied', 403)
    tasks = list(task.id for task in engine.Task.objects(course=course.obj))
    return HTTPResponse(f'get {course}\'s tasks', data=tasks)


@task_api.post('/')
@Request.json(
    'course: str',
    'title: str',
    'content',
    'starts_at',
    'ends_at',
)
@Request.doc('course', Course)
@login_required
def add_task(
    user: User,
    course: Course,
    title: str,
    content: Optional[str],
    starts_at: Optional[str],
    ends_at: Optional[str],
):
    if not course.permission(user=user, req=Course.Permission.WRITE):
        return HTTPError('Not enough permission', 403)
    try:
        if starts_at is not None:
            starts_at = parser.parse(starts_at)
        if ends_at is not None:
            ends_at = parser.parse(ends_at)
    except parser.ParserError:
        return HTTPError('Invalid or unknown string format', 400)
    try:
        task = Task.add(
            course=course,
            title=title,
            content=content,
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


@task_api.put('/<_id>')
@Request.json(
    'title',
    'content',
    'starts_at',
    'ends_at',
)
@Request.doc('_id', 'task', Task)
@login_required
def edit_task(
    user: User,
    task: Task,
    title: Optional[str],
    content: Optional[str],
    starts_at: Optional[str],
    ends_at: Optional[str],
):
    if not Course(task.course).permission(
            user=user,
            req=Course.Permission.WRITE,
    ):
        return HTTPError('Not enough permission', 403)
    try:
        if starts_at is not None:
            starts_at = parser.parse(starts_at)
        if ends_at is not None:
            ends_at = parser.parse(ends_at)
    except parser.ParserError:
        return HTTPError('Invalid or unknown string format', 400)
    try:
        task.update(**drop_none({
            'title': title,
            'content': content,
            'starts_at': starts_at,
            'ends_at': ends_at,
        }))
    except engine.ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())
    return HTTPResponse('success')


@task_api.delete('/<_id>')
@Request.doc('_id', 'task', Task)
@login_required
def delete_task(user: User, task: Task):
    if not Course(task.course).permission(
            user=user,
            req=Course.Permission.WRITE,
    ):
        return HTTPError('Not enough permission', 403)
    task.delete()
    return HTTPResponse('success')


@task_api.get('/<_id>')
@Request.doc('_id', 'task', Task)
@login_required
def get_task(user: User, task: Task):
    if not Course(task.course).permission(
            user=user,
            req=Course.Permission.READ,
    ):
        return HTTPError('Permission denied', 403)
    data = task.to_dict()
    data['progress'] = task.progress(user)
    return HTTPResponse(f'success', data=data)


@task_api.post('/<_id>/solve-oj-problem')
@Request.json('problems: list', 'sync')
@Request.doc('_id', 'task', Task)
@login_required
def add_solve_OJ_problem_requirement(
    user: User,
    task: Task,
    problems: List[int],
    sync: Optional[bool],
):
    if not Course(task.course).permission(
            user=user,
            req=Course.Permission.WRITE,
    ):
        return HTTPError('Not enough permission', 403)
    try:
        problems = [*map(Problem, problems)]
        requirement = SolveOJProblem.add(task=task, problems=problems)
        if sync == True:
            requirement.sync()
        return HTTPResponse(f'success', data=requirement.id)
    except engine.DoesNotExist as e:
        return HTTPError(e, 400)
    except ValueError as ve:
        return HTTPError(ve, 400, data=str(ve))
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())


@task_api.post('/<_id>/leave-comment')
@Request.json('problem: int', 'required_number', 'acceptance', 'sync')
@Request.doc('_id', 'task', Task)
@Request.doc('problem', Problem)
@login_required
def add_solve_comment_requirement(
    user: User,
    task: Task,
    problem: Problem,
    required_number: Optional[int],
    acceptance: Optional[int],
    sync: Optional[bool],
):
    if not Course(task.course).permission(
            user=user,
            req=Course.Permission.WRITE,
    ):
        return HTTPError('Not enough permission', 403)
    try:
        requirement = LeaveComment.add(
            task=task,
            problem=problem,
            required_number=required_number,
            acceptance=acceptance,
        )
        if sync == True:
            requirement.sync()
        return HTTPResponse(f'success', data=requirement.id)
    except ValueError as ve:
        return HTTPError(ve, 400, data=str(ve))
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())


@task_api.post('/<_id>/reply-to-comment')
@Request.json('required_number: int', 'sync')
@Request.doc('_id', 'task', Task)
@login_required
def add_reply_to_comment_requirement(
    user: User,
    task: Task,
    required_number: int,
    sync: Optional[bool],
):
    if not Course(task.course).permission(
            user=user,
            req=Course.Permission.WRITE,
    ):
        return HTTPError('Not enough permission', 403)
    try:
        requirement = ReplyToComment.add(
            task=task,
            required_number=required_number,
        )
        if sync == True:
            requirement.sync()
        return HTTPResponse(f'success', data=requirement.id)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())


@task_api.post('/<_id>/like-others-comment')
@Request.json('required_number: int', 'sync')
@Request.doc('_id', 'task', Task)
@login_required
def add_like_others_comment_requirement(
    user: User,
    task: Task,
    required_number: int,
    sync: Optional[bool],
):
    if not Course(task.course).permission(
            user=user,
            req=Course.Permission.WRITE,
    ):
        return HTTPError('Not enough permission', 403)
    try:
        requirement = LikeOthersComment.add(
            task=task,
            required_number=required_number,
        )
        if sync == True:
            requirement.sync()
        return HTTPResponse(f'success', data=requirement.id)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())
