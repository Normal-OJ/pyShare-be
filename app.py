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
        # if we can find the pre defined user
        if username in USER_DATA:
            # if he/she haven't sing up
            if not User(username):
                user_data = USER_DATA[username]
                u = User.signup(
                    email=user_data['email'],
                    username=user_data['username'],
                    password=user_data['password'],
                )
                # update user's role if specified
                u.update(role=user_data.get('role', u.role))
        else:
            logging.error(
                f'Try to setup with user that is not in user.json: {username}')


def setup_tag(tags):
    with open('env_data/tag/tag.json') as f:
        TAG_DATA = json.load(f)
    for tag in tags:
        # if we can find the pre defined tag
        if tag in TAG_DATA:
            # the tag haven't add to DB
            if not Tag(tag):
                tag_data = TAG_DATA[tag]
                Tag.add(value=tag_data['value'])
        else:
            logging.error(
                f'Try to setup with tag that is not in tag.json: {tag}')


def setup_course(courses):
    with open('env_data/course/course.json') as f:
        COURSE_DATA = json.load(f)
    for course in courses:
        # if we can find the pre defined course and it is not exist
        if course in COURSE_DATA:
            if not Course(course):
                course_data = COURSE_DATA[course]
                c = Course.add(
                    name=course_data['name'],
                    teacher=course_data['teacher'],
                )
                # add tags if specified
                tags = course_data.get('tags')
                if tags is not None:
                    tags = [*map(Tag, tags)]
                    for t in filter(lambda t: not t, tags):
                        logging.error(f'No Such Tag: {t} in {c}')
                    c.update(tags=[t.obj for t in filter(bool, tags)])
                # add students if specified
                students = course_data.get('students')
                if students is not None:
                    # convert to MongoBase
                    students = [*map(User, students)]
                    # log non-exist user
                    for s in filter(lambda s: not s, students):
                        logging.error(f'No Such User: {s} in {c}')
                    # filter valid users
                    students = [s.obj for s in filter(bool, students)]
                    # update references
                    for s in students:
                        s.update(course=c.obj)
                    c.update(push_all__students=students)
                # add problems if specified !!! NOT DONE YET !!!
                problems = course_data.get('problems')
                if problems is not None:
                    problems = [*map(Problem, problems)]
                    for p in filter(lambda p: not p, problems):
                        logging.error(f'No Such Problem: {p} in {c}')
                    c.update(push_all__problems=[
                        p.obj for p in filter(bool, problems)
                    ])
        else:
            logging.error(
                f'Try to setup with course that is not in course.json: {course}'
            )


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
        ('tag', setup_tag),
        ('course', setup_course),
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
