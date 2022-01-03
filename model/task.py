from flask import Blueprint

from mongo import *
from mongo import engine
from .course import *
from .utils import *
from .auth import *

__all__ = ['task_api']

task_api = Blueprint('task_api', __name__)


@course_api.get('/<course>/tasks')
@Request.doc('course', Course)
@login_required
def get_task_list(user, course):
    if not course.permission(user=user, req='r'):
        return HTTPError('Permission denied', 403)
    tasks = list(task.id for task in engine.Task.objects(course=course.obj))
    return HTTPResponse(f'get {course}\'s tasks', data=tasks)


@task_api.post('/')
@Request.json('course: str', 'title', 'content', 'starts_at', 'ends_at')
@Request.doc('course', Course)
@login_required
def add_task(user, course, title, content, starts_at, ends_at):
    if not course.permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
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


@task_api.get('/<_id>')
@Request.doc('_id', 'task', Task)
@login_required
def get_task(user, task):
    if not Course(task.course).permission(user=user, req='r'):
        return HTTPError('Permission denied', 403)
    data = task.to_dict()
    data['progress'] = task.progress(user)
    return HTTPResponse(f'success', data=data)


@task_api.post('/<_id>/solve-oj-problem')
@Request.json('problems: list', 'sync')
@Request.doc('_id', 'task', Task)
@login_required
def add_solve_OJ_problem_requirement(user, task, problems, sync):
    if not Course(task.course).permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    try:
        problems = [*map(Problem, problems)]
        requirement = SolveOJProblem.add(task=task, problems=problems)
        if sync == True:
            requirement.sync(task.course.students)
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
    user,
    task,
    problem,
    required_number,
    acceptance,
    sync,
):
    if not Course(task.course).permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    try:
        requirement = LeaveComment.add(
            task=task,
            problem=problem,
            required_number=required_number,
            acceptance=acceptance,
        )
        if sync == True:
            requirement.sync(task.course.students)
        return HTTPResponse(f'success', data=requirement.id)
    except ValueError as ve:
        return HTTPError(ve, 400, data=str(ve))
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())


@task_api.post('/<_id>/reply-to-comment')
@Request.json('required_number', 'sync')
@Request.doc('_id', 'task', Task)
@login_required
def add_reply_to_comment_requirement(
    user,
    task,
    required_number,
    sync,
):
    if not Course(task.course).permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    try:
        requirement = ReplyToComment.add(
            task=task,
            required_number=required_number,
        )
        if sync == True:
            requirement.sync(task.course.students)
        return HTTPResponse(f'success', data=requirement.id)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())


@task_api.post('/<_id>/like-others-comment')
@Request.json('required_number: int', 'sync')
@Request.doc('_id', 'task', Task)
@login_required
def add_like_others_comment_requirement(
    user,
    task,
    required_number,
    sync,
):
    if not Course(task.course).permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    try:
        requirement = LikeOthersComment.add(
            task=task,
            required_number=required_number,
        )
        if sync == True:
            requirement.sync(task.course.students)
        return HTTPResponse(f'success', data=requirement.id)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())
