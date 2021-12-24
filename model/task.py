from flask import Blueprint, request

from mongo import *
from mongo import engine
from .course import *
from .utils import *
from .auth import *

__all__ = ['task_api']

task_api = Blueprint('task_api', __name__)


@course_api.route('/<course>/tasks', methods=['GET'])
@Request.doc('course', Course)
@login_required
def get_task_list(user, course):
    tasks = list(task.id for task in engine.Task.objects(course=course.obj))
    return HTTPResponse(f'get {course}\'s tasks', data=tasks)


@task_api.route('/', methods=['POST'])
@Request.json('course: str', 'starts_at', 'ends_at')
@Request.doc('course', Course)
@identity_verify(0, 1)
def add_task(user, course, starts_at, ends_at):
    if not course.permission(user=user, req={'r'}):
        return HTTPError('Not enough permission', 403)
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
    return HTTPResponse(f'success', data=task.to_mongo().to_dict())


@task_api.route('/<_id>/solve-oj-problem', methods=['POST'])
@Request.json('problems: list')
@Request.doc('_id', 'task', Task)
@login_required
def add_solve_OJ_problem_requirement(user, task, problems):
    if not Course(task.course).permission(user=user, req={'r'}):
        return HTTPError('Not enough permission', 403)
    try:
        problems = map(Problem, problems)
        requirement = SolveOJProblem.add(task=task, problems=problems)
        return HTTPResponse(f'success', data=requirement.id)
    except engine.DoesNotExist as e:
        return HTTPError(e, 400)
    except ValueError as ve:
        return HTTPError(ve, 400, data=ve)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())


@task_api.route('/<_id>/leave-comment', methods=['POST'])
@Request.json('problem: int', 'required_number', 'acceptance')
@Request.doc('_id', 'task', Task)
@Request.doc('problem', Problem)
@login_required
def add_solve_comment_requirement(user, task, problem, required_number,
                                  acceptance):
    if not Course(task.course).permission(user=user, req={'r'}):
        return HTTPError('Not enough permission', 403)
    try:
        requirement = LeaveComment.add(
            task=task,
            problem=problem,
            required_number=required_number,
            acceptance=acceptance,
        )
        return HTTPResponse(f'success', data=requirement.id)
    except ValueError as ve:
        return HTTPError(ve, 400, data=ve)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())


@task_api.route('/<_id>/reply-to-comment', methods=['POST'])
@Request.json('required_number')
@Request.doc('_id', 'task', Task)
@login_required
def add_reply_to_comment_requirement(user, task, required_number):
    if not Course(task.course).permission(user=user, req={'r'}):
        return HTTPError('Not enough permission', 403)
    try:
        requirement = ReplyToComment.add(task=task,
                                         required_number=required_number)
        return HTTPResponse(f'success', data=requirement.id)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())


@task_api.route('/<_id>/like-others-comment', methods=['POST'])
@Request.json('required_number: int')
@Request.doc('_id', 'task', Task)
@login_required
def add_like_others_comment_requirement(user, task, required_number):
    if not Course(task.course).permission(user=user, req={'r'}):
        return HTTPError('Not enough permission', 403)
    try:
        requirement = LikeOthersComment.add(task=task,
                                            required_number=required_number)
        return HTTPResponse(f'success', data=requirement.id)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())
