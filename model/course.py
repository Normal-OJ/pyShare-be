from functools import partial
from typing import Union
from flask import Blueprint, send_file, request
from .utils import *
from .auth import *
from mongo import *
from mongo import engine

__all__ = ['course_api']

course_api = Blueprint('course_api', __name__)


@course_api.route('/', methods=['GET'])
@login_required
def course_list(user):
    '''
    get a list of course with course name and teacher's name
    '''
    cs = map(Course, engine.Course.objects)
    cs = [{
        'id': c.id,
        'name': c.name,
        'teacher': c.teacher.info,
        'description': c.description,
        'year': c.year,
        'semester': c.semester,
        'status': c.status,
    } for c in cs if c.permission(
        user=user,
        req={'r'},
    )]
    return HTTPResponse('here you are', data=cs)


@course_api.route('/<course>', methods=['GET'])
@login_required
@Request.doc('course', Course)
def get_single_course(user, course):
    if not course.permission(user=user, req={'r'}):
        return HTTPError('Not enough permission', 403)
    comments_of_problems = [
        p.comments for p in course.problems if not p.is_template
    ]
    ret = {
        'name': course.name,
        'id': course.id,
        'teacher': course.teacher.info,
        'students': [s.info for s in course.students],
        'numOfProblems': len(comments_of_problems),
        'numOfComments': sum(map(len, comments_of_problems)),
        'description': course.description,
        'year': course.year,
        'semester': course.semester,
        'status': course.status,
    }
    return HTTPResponse('here you are', data=ret)


@course_api.route('/<course>/statistic', methods=['GET'])
@course_api.route('/<course>/statistic/problem', methods=['GET'])
@login_required
@Request.doc('course', Course)
def statistic(user, course):
    if not course.permission(user=user, req={'p'}):
        return HTTPError('Not enough permission', 403)
    users = map(User, course.students)
    ret = []
    for u in users:
        s = u.statistic([course.obj])
        s.update({'info': u.info})
        ret.append(s)
    return HTTPResponse('ok', data=ret)


@course_api.route('/<course>/statistic/oj-problem', methods=['GET'])
@login_required
@Request.args('pids')
@Request.doc('course', Course)
def oj_statistic(user, course, pids: str):
    if not course.permission(user=user, req={'p'}):
        return HTTPError('Not enough permission', 403)
    if pids == '' or pids is None:
        return HTTPError('pids are required', 400)
    try:
        pids = [int(pid) for pid in pids.split(',')]
    except ValueError:
        return HTTPError('Invalid pid value', 400)
    problems = [Problem(pid) for pid in pids]
    if not all(problems):
        return HTTPError('Problem not found', 404)
    if any(p not in course.problems for p in problems):
        return HTTPError(f'All problems must belong to {course}', 400)
    return HTTPResponse(data=course.oj_statistic(problems))


@course_api.route('/<name>/permission', methods=['GET'])
@login_required
@Request.doc('name', 'course', Course)
def permission(user, course):
    return HTTPResponse('ok', data=list(course.own_permission(user=user)))


@course_api.route('/<name>', methods=['DELETE'])
@login_required
@Request.doc('name', 'course', Course)
def delete_course(user, course):
    if not course.permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    course.delete()
    return HTTPResponse('success')


@course_api.route('/', methods=['POST'])
@Request.json(
    'name: str',
    'teacher: str',
    'description: str',
    'year: int',
    'semester: int',
    'status: int',
)
@Request.doc('teacher', 'teacher', User)
@identity_verify(0, 1)  # only admin and teacher can call this route
def create_course(
    user,
    **c_ks,
):
    try:
        c = Course.add(**c_ks)
    except ValidationError as ve:
        return HTTPError(
            ve,
            400,
            data=ve.to_dict(),
        )
    except PermissionError as e:
        return HTTPError(e, 403)
    except NotUniqueError as e:
        return HTTPError(e, 422)
    except DoesNotExist as e:
        return HTTPError(e, 404)
    return HTTPResponse('success', data={'id': c.id})


@course_api.route('/<course>', methods=['PUT'])
@login_required
@Request.json(
    'name: str',
    'description: str',
    'year: int',
    'semester: int',
    'status: int',
)
@Request.doc('course', Course)
def update_course(
    user,
    course,
    **c_ks,
):
    if not course.permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    try:
        course.update(**c_ks)
    except ValidationError as ve:
        return HTTPError(
            ve,
            400,
            data=ve.to_dict(),
        )
    except ValueError as e:
        return HTTPError(e, 400)
    return HTTPResponse('success')


@course_api.route('/<course>/student/insert', methods=['PATCH'])
@course_api.route('/<course>/student/remove', methods=['PATCH'])
@login_required
@Request.json('users: list')
@Request.doc('course', Course)
def update_students(user, course, users):
    '''
    update course students, action should be `insert` or `remove`
    '''
    if not course.permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    # ignore duplicated user ids
    users = [*{*users}]
    # query document
    u_users = [*map(User, users)]
    # store nonexistent user ids
    not_in_db = [u.pk for u in filter(bool, u_users)]
    action = request.url[-6:]
    if action == 'insert':
        warning = [*({*course.students} & {*[u.obj for u in u_users]})]
        course.update(push_all__students=users)
    elif action == 'remove':
        warning = [*({*[u.obj for u in u_users]} - {*course.students})]
        course.update(pull_all__students=users)
        for user in u_users:
            if user.obj in warning:
                continue
            for problem in course.problems:
                if user == problem.author:
                    problem.delete()
            for comment in engine.Comment.objects(author=user.pk):
                Comment(comment).delete()
            for comment in engine.Comment.objects(liked=user.pk):
                comment.update(pull__liked=user.obj)
                user.update(pull__likes=comment)
    # some users fail
    if len(warning):
        warning = list(user.info for user in warning)
        return HTTPError(
            'fail to update students',
            400,
            data={
                'notInDB': not_in_db,
                'users': warning,
            },
        )
    return HTTPResponse('success')


@course_api.route('/<course>/tag', methods=['PATCH'])
@login_required
@Request.json('push: list', 'pop: list', 'category: int')
@Request.doc('course', Course)
def update_tags(user, course, push, pop, category):
    '''
    push/pop tags to/from course
    '''
    if not course.permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    try:
        course.patch_tag(push, pop, category)
    except ValidationError as ve:
        return HTTPError(ve, 400, data=ve.to_dict())
    except ValueError as e:
        return HTTPError(e, 400)
    except engine.DoesNotExist as e:
        return HTTPError(e, 400)
    return HTTPResponse('success')


@course_api.route('/<course>/statistic-file', methods=['GET'])
@login_required
@Request.doc('course', Course)
def get_statistic_file(user, course: Course):
    if not course.permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    f = course.statistic_file()
    return send_file(
        f,
        as_attachment=True,
        max_age=30,
        download_name=f'{course.name}-statistic.csv',
    )


def complete_data(req: Union[Requirement, Task], user: User):
    return {
        'userInfo': user.info,
        'progress': req.progress(user),
        'completes': req.completed_at(user),
    }


@course_api.get('/<cid>/task/<tid>/record')
@login_required
@Request.doc('cid', 'course', Course)
@Request.doc('tid', 'task', Task)
def get_task_record(
    user: User,
    course: Course,
    task: Task,
):
    if not course.permission(user=user, req='w'):
        return HTTPError('Permission denied', 403)
    if course != task.course:
        return HTTPError(f'Cannot find {task} in {course}', 404)
    ret = task.to_dict()
    ret['requirements'] = [{
        'id':
        req.id,
        'cls':
        req._cls.split('.')[-1],
        'completes': [*map(
            partial(complete_data, req),
            course.students,
        )],
    } for req in task.requirements]
    return HTTPResponse(data=ret)


@course_api.get('/<cid>/task/record')
@login_required
@Request.doc('cid', 'course', Course)
def get_all_task_record(user: User, course: Course):
    if not course.permission(user=user, req='w'):
        return HTTPError('Permission denied', 403)
    ret = [{
        **t.to_dict(),
        'completes': [
            *map(
                partial(complete_data, t),
                course.students,
            ),
        ],
    } for t in Task.filter(course=course)]
    return HTTPResponse(data=ret)
