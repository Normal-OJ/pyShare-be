from flask import Blueprint
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
    cs = list({
        'name': data.name,
        'teacher': User(data.teacher.username).info
    } for data in engine.Course.objects.only('name', 'teacher'))
    return HTTPResponse('here you are', data=cs)


@course_api.route('/<name>', methods=['GET'])
@login_required
@Request.doc('name', 'course', Course)
def get_single_course(user, course):
    ret = {
        'teacher': User(course.teacher.username).info,
        'students': [User(s.username).info for s in course.students],
        'problems': [p.pid for p in course.problems]
    }
    return HTTPResponse('here you are', data=ret)


@course_api.route('/<name>/statistic', methods=['GET'])
@Request.doc('name', 'course', Course)
def statistic(course):
    ret = [User(u.username).statistic() for u in course.students]
    return HTTPResponse('666', data=ret)


@course_api.route('/<name>', methods=['DELETE'])
@login_required
@identity_verify(0)  # only admin can call this route
@Request.doc('name', 'course', Course)
def delete_course(name, course):
    course.delete()
    return HTTPResponse('success')


@course_api.route('/', methods=['POST'])
@login_required
@Request.json('name: str', 'teacher: str')
@Request.doc('teacher', 'teacher', User)
@identity_verify(0, 1)  # only admin and teacher can call this route
def create_course(user, name, teacher):
    try:
        Course.add(
            name=name,
            teacher=teacher,
        )
    except engine.ValidationError as ve:
        return HTTPError(
            str(ve),
            400,
            data=ve.to_dict(),
        )
    except (engine.NotUniqueError, PermissionError) as e:
        return HTTPError(str(e), 403)
    return HTTPResponse('success')


@course_api.route('/<name>/student/<action>', methods=['PATCH'])
@login_required
@Request.json('users: list')
@Request.doc('name', 'course', Course)
@identity_verify(0, 1)  # only admin and teacher can call this route
def update_students(user, course, users, action):
    '''
    update course students, action should be `insert` or `remove`
    '''
    # preprocess action
    if action not in {'insert', 'remove'}:
        return HTTPError('only accept action \'insert\' or \'remove\'', 400)
    # ignore duplicated usernames
    users = [*{*users}]
    # query document
    u_users = [User(i) for i in users]
    # some documents are not exist in db
    if not all(u_users):
        not_in_db = [*{n for i, n in enumerate(users) if not u_users[i]}]
    else:
        not_in_db = []
    if action == 'insert':
        warning = [*({*course.students} & {*[u.obj for u in users]})]
        course.update(push_all__students=users)
    elif action == 'remove':
        warning = [*({*[u.obj for u in users]} - {*course.students})]
        course.update(pull_all__students=users)
    # some users fail
    if len(warning) != 0:
        return HTTPError(
            'fail to update students',
            400,
            data={
                'notInDB': not_in_db,
                'users': warning,
            },
        )
    return HTTPResponse('success')


@course_api.route('/<name>/tag', methods=['PATCH'])
@login_required
@Request.json('push: list', 'pop: list')
@Request.doc('name', 'course', Course)
@identity_verify(0, 1)  # only admin and teacher can call this route
def update_tags(course, push, pop):
    '''
    push/pop tags to/from course
    '''
    for t in push:
        if not Tag(t):
            return HTTPError('Push: Tag not found', 404)
        if t in pop:
            return HTTPError('Tag appears in both list', 400)
    for t in pop:
        if t not in Course.tags:
            return HTTPError('Pop: Tag not found', 404)
    try:
        course.tags += push
        course.tags = list(set([tag for tag in course.tags if tag not in pop]))
        course.save()
    except engine.ValidationError as ve:
        return HTTPError(str(ve), 400, data=ve.to_dict())
    return HTTPResponse('success')
