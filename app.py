import json
from flask import Flask
from model import *
from mongo import *
from mongo import engine
from mongo import problem

# Create a flask app
app = Flask(__name__)
app.url_map.strict_slashes = False

# Regist flask blueprint
app.register_blueprint(auth_api, url_prefix='/auth')
app.register_blueprint(problem_api, url_prefix='/problem')
app.register_blueprint(test_api, url_prefix='/test')
app.register_blueprint(post_api, url_prefix='/post')
app.register_blueprint(user_api, url_prefix='/user')


def setup_user(usernames):
    with open('env_data/user/user.json') as f:
        USER_DATA = json.load(f)
    for username in usernames:
        User.signup(**USER_DATA[username])


def setup_comment(comments):
    pass


def setup_problem(problems):
    pass


def setup_app(config=None, env=None, testing=True):
    '''
    setup flask app from config and pre-configed env
    '''
    # force testing, can be overwritten
    app.config['TESTING'] = testing
    # read config from pyfile
    if config:
        app.config.from_pyfile(config)
    # setup environment for testing
    if env:
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
    return app


if not User("first_admin"):
    ADMIN = {
        'username': 'first_admin',
        'password': 'firstpasswordforadmin',
        'email': 'i.am.first.admin@noj.tw'
    }

    admin = User.signup(**ADMIN)
    admin.update(active=True, role=0)

if Number("serial_number").obj is None:
    engine.Number(name="serial_number").save()

problem.number = Number("serial_number").obj.number
