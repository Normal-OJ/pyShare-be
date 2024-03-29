# Standard library
from functools import wraps
# Related third party imports
from flask import Blueprint, request, current_app
from flask.helpers import url_for
# Local application
from mongo import *
from mongo import engine
from .utils import *

import secrets
import csv
import io

__all__ = ['auth_api', 'login_required', 'identity_verify']

auth_api = Blueprint('auth_api', __name__)


class InvalidTokenError(Exception):
    '''
    raise when recieve a invalid token
    '''


def login_required(func):
    '''Check if the user is login

    Returns:
        A wrapped function
    
    Raises:
        PermissionError: Not logged in, Inactive user
        ValidationError: Invalid token, Authorization expired
    '''
    # TODO: provide more details about errors
    @Request.cookies(vars_dict={'token': 'piann'})
    def wrapper(token, *args, **kwargs):
        if token is None:
            raise InvalidTokenError('Token not found')
        json = jwt_decode(token)
        if json is None or not json.get('secret'):
            raise InvalidTokenError('Invalid token')
        user = User(json['data'].get('_id'))
        if not user:
            raise InvalidTokenError('Invalid token')
        try:
            if not secrets.compare_digest(
                    json['data'].get('userId'),
                    user.user_id,
            ):
                raise InvalidTokenError('Authorization expired')
        except TypeError:
            raise InvalidTokenError('Invalid token')
        if not user.active:
            raise InvalidTokenError('Inactive user')
        kwargs['user'] = user
        return func(*args, **kwargs)

    @wraps(func)
    def wrapper_with_exception_handling(*args, **ks):
        try:
            return wrapper(*args, **ks)
        except InvalidTokenError as e:
            # logout user
            current_app.logger.info(f'Login failed. [err={e}]')
            return HTTPRedirect(url_for('auth_api.session'))

    return wrapper_with_exception_handling


def identity_verify(*roles):
    '''Verify a logged in user's identity
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
        return HTTPResponse('Goodbye', cookies=cookies)

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
            if email is not None:
                user = User.login_by_email(email, u_ks['password'])
            else:
                missing_field = [
                    f for f in ('username', 'school') if u_ks.get(f) is None
                ]
                if len(missing_field):
                    return HTTPError(
                        'Missing field',
                        400,
                        data={'field': missing_field},
                    )
                user = User.login(**u_ks)
        except DoesNotExist:
            return HTTPError('Login Failed', 401)
        if not user.active:
            return HTTPError('Inactive User', 403)
        cookies = {'piann_httponly': user.secret, 'jwt': user.cookie}
        return HTTPResponse('Login Success', cookies=cookies)

    methods = {'GET': logout, 'POST': login}
    return methods[request.method]()


@auth_api.route('/session', methods=['PATCH'])
@login_required
@Request.json('fields: list')
def update_session(user, fields):
    try:
        cookies = {
            'piann_httponly': user.secret,
            'jwt': user.cookie(fields),
        }
    except ValueError as e:
        return HTTPError(str(e), 400)
    return HTTPResponse(cookies=cookies)


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
@Request.json('csv_string: str', 'course')
@login_required
def batch_signup(user, csv_string, course):
    # Check course
    if course is not None:
        course = Course(course)
        if not course:
            return HTTPError(f'{course} not found', 404)
        if not course.permission(user=user, req=Course.Permission.WRITE):
            return HTTPError('Not enough permission', 403)
    # Read csv
    user_data = [*csv.DictReader(io.StringIO(csv_string))]
    if len(user_data) == 0:
        return HTTPError('Invalid csv format', 400)
    # Validate keys
    required_keys = {
        'username',
        'school',
        'password',
        'displayName',
    }
    if required_keys - {*user_data[0].keys()}:
        return HTTPError('Invalid csv format', 400)
    users = {}
    fails = []
    exists = set()
    for _u in user_data:
        try:
            # Try to find user on system
            new_user = User(
                User.engine.objects.get(
                    username=_u['username'],
                    school=_u['school'],
                ))
            user_key = (_u['school'], _u['username'])
            exists.add(user_key)
            users[':'.join(user_key)] = new_user.pk
            # add to course
            if course:
                course.add_student(new_user)
        except DoesNotExist:
            # get role
            role = _u.get('role', engine.User.Role.STUDENT)
            if role == '':
                role = engine.User.Role.STUDENT
            try:
                role = int(role)
            except ValueError:
                return HTTPError('Role needs to be int', 400)
            # Try to register a non-student user
            # But the client is not admin
            if role < engine.User.Role.STUDENT and user < 'admin':
                return HTTPError('Only admins can change roles', 403)
            # sign up a new user
            try:
                new_user = User.signup(
                    username=_u['username'],
                    password=_u['password'],
                    display_name=_u['displayName'],
                    school=_u['school'],
                    course=getattr(course, 'obj', None),
                    role=role,
                )
                users[':'.join((_u['school'], _u['username']))] = new_user.pk
            except (ValidationError, ValueError) as e:
                err = str(e)
                fails.append({
                    'username': _u['username'],
                    'school': _u['school'],
                    'err': err,
                })
                current_app.logger.error(
                    f'fail to sign up for {_u["username"]}\n'
                    f'error: {err}\n', )
    if exists or fails:
        exists = [{
            'username': e[1],
            'school': e[0],
        } for e in exists]
        return HTTPError(
            'Sign up finish, but some issues occurred.',
            400,
            data={
                'fails': fails,
                'exist': exists,
                'users': users,
            },
        )
    return HTTPResponse('Ok.', data={'users': users})


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
        user = User.get_by_email(email)
    except DoesNotExist:
        return HTTPError('User Not Exists', 404)
    new_password = secrets.token_urlsafe()
    user_id2 = hash_id(user.username, new_password)
    user.update(user_id2=user_id2)
    send_noreply([email], '[Python 創作分享平台] 密碼復原信',
                 f'請使用這組替代密碼進行登入：{new_password}，並於登入後更換密碼。\n')
    return HTTPResponse('Recovery Email Has Been Sent')
