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
    cs = engine.Course.objects.only('name')
    cs = [Course(c.name) for c in cs]
    cs = [{
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


@course_api.route('/<name>', methods=['GET'])
@login_required
@Request.doc('name', 'course', Course)
def get_single_course(user, course):
    if not course.permission(user=user, req={'r'}):
        return HTTPError('Not enough permission', 403)
    comments_of_problems = [
        p.comments for p in course.problems if not p.is_template
    ]
    ret = {
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


@course_api.route('/<name>/statistic', methods=['GET'])
@login_required
@Request.doc('name', 'course', Course)
def statistic(user, course):
    if not course.permission(user=user, req={'r'}):
        return HTTPError('Not enough permission', 403)
    users = map(User, course.students)
    ret = []
    for u in users:
        s = u.statistic({course.obj})
        s.update({'info': u.info})
        ret.append(s)
    return HTTPResponse('ok', data=ret)


@course_api.route('/<name>/permission', methods=['GET'])
@login_required
@Request.doc('name', 'course', Course)
def permission(user, course):
    return HTTPResponse('ok', data=list(course.permission(user=user)))


@course_api.route('/<name>', methods=['DELETE'])
@login_required
@Request.doc('name', 'course', Course)
def delete_course(user, course):
    if not course.permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    course.delete()
    return HTTPResponse('success')


@course_api.route('/', methods=['POST'])
@login_required
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
        Course.add(**c_ks)
    except ValidationError as ve:
        return HTTPError(
            str(ve),
            400,
            data=ve.to_dict(),
        )
    except PermissionError as e:
        return HTTPError(str(e), 403)
    except NotUniqueError as e:
        return HTTPError(str(e), 422)
    return HTTPResponse('success')


@course_api.route('/<name>', methods=['PUT'])
@login_required
@Request.json(
    'description: str',
    'year: int',
    'semester: int',
    'status: int',
)
@Request.doc('name', 'course', Course)
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
            str(ve),
            400,
            data=ve.to_dict(),
        )
    except ValueError as e:
        return HTTPError(str(e), 400)
    return HTTPResponse('success')


@course_api.route('/<name>/student/insert', methods=['PATCH'])
@course_api.route('/<name>/student/remove', methods=['PATCH'])
@login_required
@Request.json('users: list')
@Request.doc('name', 'course', Course)
def update_students(user, course, users, action):
    '''
    update course students, action should be `insert` or `remove`
    '''
    if not course.permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    # ignore duplicated usernames
    users = [*{*users}]
    # query document
    u_users = [*map(User, users)]
    # store nonexistent usernames
    not_in_db = [u.pk for u in filter(bool, u_users)]
    action = request.url_rule[-6:]
    if action == 'insert':
        warning = [*({*course.students} & {*[u.obj for u in u_users]})]
        course.update(push_all__students=users)
    elif action == 'remove':
        warning = [*({*[u.obj for u in u_users]} - {*course.students})]
        course.update(pull_all__students=users)
    # some users fail
    if len(warning):
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
@Request.json(
    'push: list',
    'pop: list',
)
@Request.doc('name', 'course', Course)
def update_tags(user, course, push, pop):
    '''
    push/pop tags to/from course
    '''
    if not course.permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    if not all(map(Tag, push)):
        return HTTPError('Push: Tag not found', 404)
    if {*pop} & {*push}:
        return HTTPError('Tag appears in both list', 400)
    if {*push} & {*course.tags}:
        return HTTPError('Push: Tag is already in course', 400)
    if {*pop} - {*course.tags}:
        return HTTPError('Pop: Tag not found', 404)
    try:
        course.patch_tag(push, pop)
    except ValidationError as ve:
        return HTTPError(str(ve), 400, data=ve.to_dict())
    return HTTPResponse('success')


@course_api.route('/<name>/statistic-file', methods=['GET'])
@login_required
@Request.doc('name', 'course', Course)
def get_statistic_file(user, course: Course):
    if not course.permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    f = course.statistic_file()
    return send_file(
        f,
        as_attachment=True,
        cache_timeout=30,
        attachment_filename=f'{course.name}-statistic.csv',
    )
