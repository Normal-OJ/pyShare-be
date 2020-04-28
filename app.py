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
            logging.error(
                f'Try to setup with user that is not in user.json: {username}')


def setup_tag(tags):
    with open('env_data/tag/tag.json') as f:
        TAG_DATA = json.load(f)
    for tag in tags:
        # if we can find the pre defined user and it haven't sing up
        if tag in TAG_DATA and not Tag(tag):
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
        if course in COURSE_DATA and not Course(course):
            course_data = COURSE_DATA[course]
            c = Course.add(
                name=course_data['name'],
                teacher=course_data['teacher'],
            )

            # add tags if specified
            tags = course_data.get('tags')
            if tags is not None:
                for t in tags:
                    if not Tag(t):
                        logging.error(
                            f'No Such Tag: tag "{t}" in course "{course}"')
                        tags.remove(t)
                c.update(tags=tags)

            # add students if specified
            students = course_data.get('students')
            if students is not None:
                for s in students:
                    u = User(s)
                    if not u:
                        logging.error(
                            f'No Such User: student "{s}" in course "{course}"'
                        )
                        students.remove(s)
                    else:
                        s = u
                        u.update(course=c.obj)
                c.update(push_all__students=students)

            # add problems if specified !!! NOT DONE YET !!!
            problems = course_data.get('problems')
            if problems is not None:
                for p in problems:
                    if not Problem(p):
                        logging.error(
                            f'No Such Problem: pid "{p}" in course "{course}"')
                        problems.remove(p)
                    else:
                        p = Problem(p)
                c.update(push_all__problems=problems)
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
