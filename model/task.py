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


@task_api.route('/<_id>/solveOJProblem', methods=['POST'])
@Request.json('problems: list')
@Request.doc('_id', 'task', Task)
@login_required
def add_solve_OJ_problem_requirement(user, task, problems):
    try:
        problems = map(Problem, problems)
        requirement = SolveOJProblem.add(task=task, problems=problems)
        return HTTPResponse(f'success', data=requirement)
    except engine.DoesNotExist as e:
        return HTTPError(e, 400)
    except ValueError as ve:
        return HTTPError(ve, 400, data=ve)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())


@task_api.route('/<_id>/leaveComment', methods=['POST'])
@Request.json('problem: int', 'required_number', 'acceptance')
@Request.doc('_id', 'task', Task)
@Request.doc('_id', 'problem', Problem)
@login_required
def add_solve_comment_requirement(user, task, problem, required_number,
                                  acceptance):
    try:
        requirement = LeaveComment.add(
            task=task,
            problem=problem,
            required_number=required_number,
            acceptance=acceptance,
        )
        return HTTPResponse(f'success', data=requirement)
    except ValueError as ve:
        return HTTPError(ve, 400, data=ve)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())


@task_api.route('/<_id>/replyToComment', methods=['POST'])
@Request.json('required_number')
@Request.doc('_id', 'task', Task)
@login_required
def add_reply_to_comment_requirement(user, task, required_number):
    try:
        requirement = ReplyToComment.add(task=task,
                                         required_number=required_number)
        return HTTPResponse(f'success', data=requirement)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())


@task_api.route('/<_id>/likeOthersComment', methods=['POST'])
@Request.json('required_number: int')
@Request.doc('_id', 'task', Task)
@login_required
def add_like_others_comment_requirement(user, task, required_number):
    try:
        requirement = LikeOthersComment.add(task=task,
                                            required_number=required_number)
        return HTTPResponse(f'success', data=requirement)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())
