# Standard library
from functools import wraps
# Related third party imports
from flask import Blueprint, request, current_app
# Local application
from mongo import *
from mongo.utils import hash_id
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
        - 401 Not Logged In
        - 401 Invalid Token
        - 403 Inactive User
    '''
    @wraps(func)
    @Request.cookies(vars_dict={'token': 'piann'})
    def wrapper(token, *args, **kwargs):
        if token is None:
            return HTTPError('Not Logged In', 401)
        json = jwt_decode(token)
        if json is None or not json.get('secret'):
            return HTTPError('Invalid Token', 401)
        user = User(json['data']['username'])
        if json['data'].get('userId') != user.user_id:
            return HTTPError(f'Authorization Expired', 403)
        if not user.active:
            return HTTPError('Inactive User', 403)
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

    @Request.json('username: str', 'password: str')
    def login(username, password):
        '''Login a user.
        Returns:
            - 400 Incomplete Data
            - 401 Login Failed
        '''
        try:
            user = User.login(username, password)
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
)
@Request.doc('course', Course)
def signup(username, password, course, email=None):
    try:
        user = User.signup(username, password, email, course.obj)
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

    user_data = csv.DictReader(io.StringIO(csv_string))
    fails = {}
    exist = set()
    for _u in user_data:
        new_user = User(_u['username'])
        if not new_user:
            # get role
            role = _u.get('role', 2)
            if role == '':
                role = 2
            try:
                role = int(role)
            except ValueError:
                return HTTPError('Role needs to be int', 400)
            if role < 2 and user != 'admin':
                return HTTPError('Only admins can change roles', 403)
            # sign up a new user
            err = None
            try:
                new_user = User.signup(
                    username=_u['username'],
                    password=_u['password'],
                    email=_u.get('email', None),
                    display_name=_u['displayName'],
                    course=course.obj,
                    role=role,
                )
            except ValidationError as ve:
                err = str(ve), ve.to_dict()
                fails[_u['username']] = [*ve.to_dict().keys()][0]
            except NotUniqueError as ne:
                err = str(ne), 'EMAIL_DUPLICATED'
                fails[_u['username']] = 'email'
            if err is not None:
                current_app.logger.error(
                    f'fail to sign up for {new_user}\n'
                    f'error: {err[0]}\n'
                    f'data: {err[1]}', )
        else:
            exist.add(_u['username'])
            # add to course
            new_user.update(add_to_set__courses=course.obj)
            course.update(add_to_set__students=new_user.obj)
    return HTTPResponse(
        'sign up finish',
        data={
            'fails': fails,
            'exist': list(exist),
        },
    )


@auth_api.route('/change-password', methods=['POST'])
@login_required
@Request.json('old_password: str', 'new_password: str')
def change_password(user, old_password, new_password):
    try:
        User.login(user.username, old_password)
    except DoesNotExist:
        return HTTPError('Wrong Password', 403)
    user.change_password(new_password)
    cookies = {'piann_httponly': user.secret}
    return HTTPResponse('Password Has Been Changed', cookies=cookies)


@auth_api.route('/check/<item>', methods=['POST'])
def check(item):
    '''Checking when the user is registing.
    '''
    @Request.json('username: str')
    def check_username(username):
        try:
            User.get_by_username(username)
        except DoesNotExist:
            return HTTPResponse('Username Can Be Used', data={'valid': 1})
        return HTTPResponse('User Exists', data={'valid': 0})

    @Request.json('email: str')
    def check_email(email):
        try:
            User.get_by_email(email)
        except DoesNotExist:
            return HTTPResponse('Email Can Be Used', data={'valid': 1})
        return HTTPResponse('Email Has Been Used', data={'valid': 0})

    method = {'username': check_username, 'email': check_email}.get(item)
    return method() if method else HTTPError('Ivalid Checking Type', 400)


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
        user = User(json['data']['username'])
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
        user = User(json['data']['username'])
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
    send_noreply(
        [email], '[N-OJ] Password Recovery',
        f'Your alternative password is {new_password}.\nPlease login and change your password.'
    )
    return HTTPResponse('Recovery Email Has Been Sent')
