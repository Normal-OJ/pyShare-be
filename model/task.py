from flask import Blueprint
from dateutil import parser

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
def add_task(user, course, title, content, starts_at, ends_at):
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
    'title: str',
    'content',
    'starts_at',
    'ends_at',
)
@Request.doc('_id', 'task', Task)
@login_required
def edit_task(user, task, title, content, starts_at, ends_at):
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
        old_starts_at = task.starts_at
        old_ends_at = task.ends_at
        task.update(**drop_none(
            title=title,
            content=content,
            starts_at=starts_at,
            ends_at=ends_at,
        ))
        task.reload()
        if task.starts_at > old_starts_at or task.ends_at < old_ends_at:
            task.update(records={})
            task.reload()
            for req in task.requirements:
                req.sync(
                    starts_at=task.starts_at,
                    ends_at=task.ends_at,
                )
        else:
            if task.starts_at < old_starts_at:
                for req in task.requirements:
                    req.sync(
                        starts_at=task.starts_at,
                        ends_at=old_starts_at,
                    )
            if task.ends_at > old_ends_at:
                for req in task.requirements:
                    req.sync(
                        starts_at=old_ends_at,
                        ends_at=task.ends_at,
                    )
    except engine.ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())
    return HTTPResponse('success')


@task_api.delete('/<_id>')
@Request.doc('_id', 'task', Task)
@login_required
def delete_task(user, task):
    if not course.permission(user=user, req=Course.Permission.WRITE):
        return HTTPError('Not enough permission', 403)
    task.delete()
    return HTTPResponse('success')


@task_api.get('/<_id>')
@Request.doc('_id', 'task', Task)
@login_required
def get_task(user, task):
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
def add_solve_OJ_problem_requirement(user, task, problems, sync):
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
    user,
    task,
    problem,
    required_number,
    acceptance,
    sync,
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
    user,
    task,
    required_number,
    sync,
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
    user,
    task,
    required_number,
    sync,
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


@task_api.delete('/<_id>/requirement')
@Request.doc('_id', 'requirement', Requirement)
@login_required
def delete_requirement(requirement):
    if not Course(task.course).permission(
            user=user,
            req=Course.Permission.WRITE,
    ):
        return HTTPError('Not enough permission', 403)
    requirement.delete()
    return HTTPResponse(f'success', data=requirement.id)
