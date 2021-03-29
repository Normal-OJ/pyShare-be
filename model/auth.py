# Standard library
from functools import wraps
# Related third party imports
from flask import Blueprint, request, current_app
# Local application
from mongo import *
from mongo import engine
from .utils import *

import secrets
import csv
import io

__all__ = ['auth_api', 'login_required', 'identity_verify']

auth_api = Blueprint('auth_api', __name__)


def login_required(func):
    '''Check if the user is login

    Returns:
        - A wrapped function
        - 401 Not logged in
        - 401 Invalid token
        - 403 Inactive user
        - 403 Authorization expired
    '''
    @wraps(func)
    @Request.cookies(vars_dict={'token': 'piann'})
    def wrapper(token, *args, **kwargs):
        if token is None:
            return HTTPError('Not logged in', 401)
        json = jwt_decode(token)
        if json is None or not json.get('secret'):
            return HTTPError('Invalid token', 401)
        try:
            user = User(json['data'].get('_id'))
        except ValidationError:
            return HTTPError('Invalid token', 401)
        if not user:
            return HTTPError('Invalid token', 401)
        try:
            if not secrets.compare_digest(
                    json['data'].get('userId'),
                    user.user_id,
            ):
                return HTTPError(f'Authorization expired', 403)
        except TypeError:
            return HTTPError('Invalid token', 401)
        if not user.active:
            return HTTPError('Inactive user', 403)
        kwargs['user'] = user
        return func(*args, **kwargs)

    return wrapper


def identity_verify(*roles):
    '''Verify a logged in user's identity

    You can find an example in `model/test.py`
    '''
    def verify(func):
        @wraps(func)
        @login_required
        def wrapper(user, *args, **kwargs):
            if user.role not in roles:
                return HTTPError('Insufficient Permissions', 403)
            kwargs['user'] = user
            return func(*args, **kwargs)

        return wrapper

    return verify


@auth_api.route('/session', methods=['GET', 'POST'])
def session():
    '''Create a session or remove a session.
    Request methods:
        GET: Logout
        POST: Login
    '''
    def logout():
        '''Logout a user.
        Returns:
            - 200 Logout Success
        '''
        cookies = {'jwt': None, 'piann': None}
        return HTTPResponse(f'Goodbye', cookies=cookies)

    @Request.json(
        'school',
        'username',
        'password: str',
        'email',
    )
    def login(email, **u_ks):
        '''Login a user.
        Returns:
            - 400 Incomplete Data
            - 401 Login Failed
        '''
        try:
            # login by email
            if email is not None:
                user = User.login_by_email(email, u_ks['password'])
            # login by username and school
            else:
                user = User.login(**u_ks)
        except DoesNotExist:
            return HTTPError('Login Failed', 401)
        if not user.active:
            return HTTPError('Inactive User', 403)
        cookies = {'piann_httponly': user.secret, 'jwt': user.cookie}
        return HTTPResponse('Login Success', cookies=cookies)

    methods = {'GET': logout, 'POST': login}
    return methods[request.method]()


@auth_api.route('/signup', methods=['POST'])
@Request.json(
    'username: str',
    'password: str',
    'email',
    'course: str',
    'school: str',
)
@Request.doc('course', Course)
def signup(
    username,
    password,
    email,
    school,
    course,
):
    try:
        User.signup(
            username=username,
            password=password,
            email=email,
            school=school,
            course=course.obj,
        )
    except ValidationError as ve:
        return HTTPError('Signup Failed', 400, data=ve.to_dict())
    except NotUniqueError as ne:
        return HTTPError('User Exists', 400)
    # verify_link = f'https://noj.tw/api/auth/active/{user.cookie}'
    # send_noreply([email], '[N-OJ] Varify Your Email', verify_link)
    return HTTPResponse('Signup Success')


@auth_api.route('/batch-signup', methods=['POST'])
@Request.json('csv_string: str', 'course: str')
@Request.doc('course', Course)
@login_required
def batch_signup(user, csv_string, course):
    if not course.permission(user=user, req={'w'}):
        return HTTPError('Not enough permission', 403)
    user_data = [*csv.DictReader(io.StringIO(csv_string))]
    if len(user_data) == 0:
        return HTTPError('Invalid csv format', 400)
    required_keys = {
        'username',
        'school',
        'password',
        'displayName',
    }
    if required_keys - {*user_data[0].keys()}:
        return HTTPError('Invalid csv format', 400)
    fails = []
    exists = set()
    for _u in user_data:
        try:
            new_user = User(
                User.engine.objects.get(
                    username=_u['username'],
                    school=_u['school'],
                ))
            exists.add((_u['username'], _u['school']))
            # add to course
            new_user.update(add_to_set__courses=course.obj)
            course.update(add_to_set__students=new_user.obj)
        except DoesNotExist:
            # get role
            role = _u.get('role', engine.User.Role.STUDENT)
            if role == '':
                role = engine.User.Role.STUDENT
            try:
                role = int(role)
            except ValueError:
                return HTTPError('Role needs to be int', 400)
            if role < engine.User.Role.STUDENT and user < 'admin':
                return HTTPError('Only admins can change roles', 403)
            # sign up a new user
            try:
                new_user = User.signup(
                    username=_u['username'],
                    password=_u['password'],
                    display_name=_u['displayName'],
                    school=_u['school'],
                    course=course.obj,
                    role=role,
                )
            except ValidationError as ve:
                fails.append({
                    'username': _u['username'],
                    'school': _u['school'],
                    'err': ve.to_dict(),
                })
                current_app.logger.error(
                    f'fail to sign up for {_u["username"]}\n'
                    f'error: {ve}\n'
                    f'data: {ve.to_dict()}', )
    if exists or fails:
        exists = [{
            'username': e[0],
            'school': e[1],
        } for e in exists]
        return HTTPError(
            'Sign up finish, but some issues occurred.',
            400,
            data={
                'fails': fails,
                'exist': exists,
            },
        )
    return HTTPResponse('Ok.')


@auth_api.route('/change/password', methods=['POST'])
@auth_api.route('/change-password', methods=['POST'])
@login_required
@Request.json('old_password: str', 'new_password: str')
def change_password(user, old_password, new_password):
    try:
        assert user == User.login(user.school, user.username, old_password)
    except (DoesNotExist, AssertionError):
        return HTTPError('Wrong Password', 403)
    user.change_password(new_password)
    cookies = {'piann_httponly': user.secret}
    return HTTPResponse('Password Has Been Changed', cookies=cookies)


@auth_api.route('/change/email', methods=['POST'])
@login_required
@Request.json(
    'password: str',
    'email: str',
)
def change_email(user, email, password):
    try:
        assert user == User.login(user.school, user.username, password)
    except (DoesNotExist, AssertionError):
        return HTTPError('Wrong password', 400)
    try:
        user.update(email=email)
    except (ValidationError, NotUniqueError):
        HTTPError('Invalid or duplicated email.', 400)
    return HTTPResponse('Email has been changed', cookies={'jwt': user.cookie})


@auth_api.route('/check/token', methods=['POST'])
@login_required
def refresh_token(user):
    return HTTPResponse(f'Welcome back!', cookies={'jwt': user.cookie})


@auth_api.route('/check/email', methods=['POST'])
@Request.json('email: str')
def check_email(email):
    try:
        engine.User.check_email(email)
    except ValidationError:
        return HTTPError('Invalid email', 400, data={'valid': 0})
    except NotUniqueError:
        return HTTPError('Duplicated email', 400, data={'valid': 0})
    return HTTPResponse('Valid email', data={'valid': 1})


@auth_api.route('/check/user-id', methods=['POST'])
@Request.json('school: str', 'username: str')
def check_user_id(school, username):
    try:
        User.engine.objects.get(
            username=username,
            school=school,
        )
    except DoesNotExist:
        return HTTPResponse('Valid user id', data={'valid': 1})
    return HTTPError('User id has been used', 400, data={'valid': 0})


@auth_api.route('/resend-email', methods=['POST'])
@Request.json('email: str')
def resend_email(email):
    try:
        user = User.get_by_email(email)
    except DoesNotExist:
        return HTTPError('User Not Exists', 404)
    if user.active:
        return HTTPError('User Has Been Actived', 400)
    verify_link = f'https://noj.tw/api/auth/active/{user.cookie}'
    send_noreply([email], '[N-OJ] Varify Your Email', verify_link)
    return HTTPResponse('Email Has Been Resent')


@auth_api.route('/active', methods=['POST'])
@auth_api.route('/active/<token>', methods=['GET'])
def active(token=None):
    '''Activate a user.
    '''
    @Request.json('display_name: str', 'agreement: bool')
    @Request.cookies(vars_dict={'token': 'piann'})
    def update(display_name, agreement, token):
        '''User: active: false -> true
        '''
        if agreement is not True:
            return HTTPError('Not Confirm the Agreement', 403)
        json = jwt_decode(token)
        if json is None or not json.get('secret'):
            return HTTPError('Invalid Token.', 403)
        user = User(json['data']['id'])
        if not user:
            return HTTPError('User Not Exists', 404)
        if user.active:
            return HTTPError('User Has Been Actived', 400)
        try:
            user.update(
                active=True,
                display_name=display_name,
            )
        except ValidationError as ve:
            return HTTPError('Failed', 400, data=ve.to_dict())
        cookies = {'jwt': user.cookie}
        return HTTPResponse('User Is Now Active', cookies=cookies)

    def redir():
        '''Redirect user to active page.
        '''
        json = jwt_decode(token)
        if json is None:
            return HTTPError('Invalid Token', 403)
        user = User(json['data']['id'])
        cookies = {'piann_httponly': user.secret, 'jwt': user.cookie}
        return HTTPRedirect('/email_verify', cookies=cookies)

    methods = {'GET': redir, 'POST': update}
    return methods[request.method]()


@auth_api.route('/password-recovery', methods=['POST'])
@Request.json('email: str')
def password_recovery(email):
    try:
        User.get_by_email(email)
    except DoesNotExist:
        return HTTPError('User Not Exists', 404)
    new_password = secrets.token_urlsafe()
    user_id2 = hash_id(user.username, new_password)
    user.update(user_id2=user_id2)
    send_noreply(
        [email],
        '[pyShare] Password Recovery',
        f'Your alternative password is {new_password}.\n'
        'Please login and change your password.',
    )
    return HTTPResponse('Recovery Email Has Been Sent')
