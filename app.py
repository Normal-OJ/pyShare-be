import json
import logging
from flask import Flask
from model import *
from mongo import *
from mongo import engine
from mongo import problem

# Create a flask app
app = Flask(__name__)
app.url_map.strict_slashes = False

# Regist flask blueprint
api2name = [
    (auth_api, '/auth'),
    (problem_api, '/problem'),
    (test_api, '/test'),
    (user_api, '/user'),
    (comment_api, '/comment'),
    (submission_api, '/submission'),
]
for api, name in api2name:
    app.register_blueprint(api, url_prefix=name)


def setup_user(usernames):
    with open('env_data/user/user.json') as f:
        USER_DATA = json.load(f)
    for username in usernames:
        # if we can find the pre defined user and it haven't sing up
        if username in USER_DATA and not User(username):
            user_data = USER_DATA[username]
            u = User.signup(
                email=user_data['email'],
                username=user_data['username'],
                password=user_data['password'],
            )
            # update user's role if specified
            role = user_data.get('role')
            if role is not None:
                u.update(role=role)
        else:
            logging.error(f'Try to setup with non-exist user {username}')


def setup_comment(comments):
    pass


def setup_problem(problems):
    pass


def setup_env(env):
    '''
    setup environment (insert document into DB)
    '''
    with open(f'env_data/env/{env}.json') as f:
        j = json.load(f)
    setup_funcs = [
        ('user', setup_user),
        ('problem', setup_problem),
        ('comment', setup_comment),
    ]
    for key, func in setup_funcs:
        if key in j:
            func(j[key])


def setup_app(config=None, env=None, testing=True):
    '''
    setup flask app from config and pre-configured env
    '''
    # force testing, can be overwritten
    app.config['TESTING'] = testing
    # read flask app config from pyfile
    if config:
        app.config.from_pyfile(config)
    # setup environment for testing
    if env:
        setup_env(env)
    return app


def gunicorn_prod_app():
    # get production app
    app = setup_app(env='prod', testing=False)
    # let flask app user gunicorn error logger
    g_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = g_logger.handlers
    app.logger.setLevel(g_logger.level)
    return app