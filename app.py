import json
import logging
from typing import Optional
from mongo.utils import logger
from flask import Flask
from flask_socketio import SocketIO
from model import *
from model.utils import *
from mongo import *
from mongo import sandbox
from mongo import engine, config as config_lib
import io


def setup_app(
    config: str = 'mongo.config.Config',
    env: Optional[str] = None,
):
    '''
    setup flask app from config and pre-configured env
    '''
    # Reserve a "empty" school
    try:
        engine.School(abbr='', name='無').save()
    except NotUniqueError:
        pass
    # Create a flask app
    app = Flask(__name__)

    # Register error handler
    @app.errorhandler(SandboxNotFound)
    def on_sandbox_not_found(_):
        return HTTPError('There are no sandbox available', 503)

    app.url_map.strict_slashes = False
    app.json_encoder = PyShareJSONEncoder
    # Override flask's config by core config
    # Note: Although the config is overridden, `ENV` and `DEBUG` should
    #   still set by env var (according to official document)
    # Ref: https://flask.palletsprojects.com/en/2.0.x/config/#environment-and-debug-features
    for k in ('TESTING', 'ENV', 'DEBUG'):
        app.config[k] = config_lib.config[k]
    # Register flask blueprint
    api2name = [
        (auth_api, '/auth'),
        (problem_api, '/problem'),
        (test_api, '/test'),
        (user_api, '/user'),
        (comment_api, '/comment'),
        (submission_api, '/submission'),
        (tag_api, '/tag'),
        (course_api, '/course'),
        (attachment_api, '/attachment'),
        (notif_api, '/notif'),
        (sandbox_api, '/sandbox'),
        (school_api, '/school'),
        (task_api, '/task'),
        (requirement_api, '/requirement'),
    ]
    for api, name in api2name:
        app.register_blueprint(api, url_prefix=name)
    if config_lib.config.get('DEBUG') == True:
        logger().warning(
            'Load dummy resource API, don\'t'
            ' use this under production mode', )
        from model.dummy import dummy_api
        app.register_blueprint(dummy_api, url_prefix='/dummy')
    # Setup SocketIO server
    socketio = SocketIO(cors_allowed_origins='*')
    socketio.on_namespace(Notifier(Notifier.namespace))
    socketio.init_app(app)
    try:
        init = engine.AppConfig.objects(key='init').get()
    except DoesNotExist:
        init = engine.AppConfig(
            id='init',
            value=True,
        ).save()
    # Setup environment for testing
    if init.value == True:
        logger().info('First run. Start setup process')
        if env is not None:
            setup_env(env)
        sandbox.init()
        init.update(value=False)
    return app


# TODO: revise setup process
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
        ('attachment', setup_attachment),
        ('problem', setup_problem),
    ]
    for key, func in setup_funcs:
        if key in j:
            func(j[key])


def gunicorn_prod_app():
    # get production app
    app = setup_app(env='prod')
    ISandbox.use(Sandbox)
    # let flask app user gunicorn error logger
    g_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = g_logger.handlers
    app.logger.setLevel(g_logger.level)
    return app


def setup_user(usernames):
    with open('env_data/user/user.json') as f:
        USER_DATA = json.load(f)
    for username in usernames:
        # if we can find the pre defined user
        if username in USER_DATA:
            user_data = USER_DATA[username]
            # if he/she haven't sing up
            try:
                u = User.signup(
                    email=user_data['email'],
                    username=user_data['username'],
                    password=user_data['password'],
                )
                # update user's role if specified
                u.update(role=user_data.get('role', u.role))
            except engine.ValidationError:
                logging.error(f'fail to sign up for {user_data["username"]}')
            except engine.NotUniqueError:
                logging.info(
                    f'{user_data["username"]} (or it\'s email) already exists in pyShare'
                )
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
                for category in tag_data['categories']:
                    Tag.add(value=tag_data['value'], category=category)
        else:
            logging.error(
                f'Try to setup with tag that is not in tag.json: {tag}')


def setup_attachment(attachments):
    with open('env_data/attachment/attachment.json') as f:
        ATTACHMENT_DATA = json.load(f)
    for attachment in attachments:
        # if we can find the pre defined attachment
        if attachment in ATTACHMENT_DATA:
            # the tag haven't add to DB
            if len(engine.Attachment.objects(filename=attachment)) == 0:
                attachment_data = ATTACHMENT_DATA[attachment]
                attachment_data['file_obj'] = io.BytesIO(
                    str.encode(attachment_data['file_obj']))
                attachment_data['author'] = User.get_by_username(
                    attachment_data['author'])
                Attachment.add(**attachment_data)
        else:
            logging.error(
                f'Try to setup with attachment that is not in attachment.json: {attachment}'
            )


def setup_course(courses):
    with open('env_data/course/course.json') as f:
        COURSE_DATA = json.load(f)
    for course in courses:
        # if we can find the pre defined course and it is not exist
        if course in COURSE_DATA:
            course_data = COURSE_DATA[course]
            teacher = User.get_by_username(course_data['teacher'])
            try:
                c = Course.add(
                    name=course_data['name'],
                    teacher=teacher,
                    year=course_data['year'],
                    semester=course_data['semester'],
                )
            except NotUniqueError:
                logging.info(f'Course {course} already exists.')
                continue
            except ValidationError as ve:
                logging.info(f'Invalid data. err: {ve.to_dict()}')
                continue
            # add tags if specified
            tags = course_data.get('tags')
            if tags is not None:
                tags = [*map(Tag, tags)]
                for t in filter(lambda t: not t, tags):
                    logging.error(f'No Such Tag: {t} in {c}')
                c.update(tags=[t.value for t in filter(bool, tags)])
            # add students if specified
            students = course_data.get('students')
            if students is not None:
                # convert to MongoBase
                students = [*map(User.get_by_username, students)]
                # log non-exist user
                for s in filter(lambda s: not s, students):
                    logging.error(f'No Such User: {s} in {c}')
                # filter valid users
                students = [s.obj for s in filter(bool, students)]
                # update references
                for s in students:
                    s.update(add_to_set__courses=c.obj)
                c.update(push_all__students=students)
            # Add problems if specified
            problems = course_data.get('problems')
            if problems is not None:
                problems = [*map(Problem, problems)]
                for p in filter(lambda p: not p, problems):
                    logging.error(f'No Such Problem: {p} in {c}')
                c.update(
                    push_all__problems=[p.obj for p in filter(bool, problems)])
        else:
            logging.error(
                f'Try to setup with course that is not in course.json: {course}'
            )


def setup_problem(problems):
    with open('env_data/problem/problem.json') as f:
        PROBLEM_DATA = json.load(f)
    for problem in problems:
        if problem in PROBLEM_DATA:
            problem_data = PROBLEM_DATA[problem]
            try:
                course = Course.get_by_name(problem_data['course']).obj
            except DoesNotExist:
                logging.error(
                    f'Course {problem_data["course"]} '
                    'doesn\'t exist.', )
                continue
            # check existence
            if Problem.filter(
                    name=problem_data['title'],
                    course=course,
            ):
                logging.info(f'Problem {problem} has been registered.')
                continue
            keys = {
                'title', 'description', 'course', 'author', 'tags',
                'default_code', 'hidden', 'allow_multiple_comments', 'extra'
            }
            ks = {v: problem_data[v] for v in problem_data.keys() & keys}
            ks['course'] = course
            if 'author' in ks:
                ks['author'] = User.get_by_username(ks['author'])
            # insert problem
            problem = Problem.add(**ks)
            # add attachments
            for att in problem_data.get('attachments', []):
                name = att['name']
                if att['source'] is None:
                    problem.insert_attachment(
                        open(
                            f'env_data/problem/attachment/{name}',
                            'rb',
                        ),
                        filename=name,
                    )
                else:
                    problem.insert_attachment(
                        None,
                        filename=name,
                        source=engine.Attachment.objects.get(
                            filename=att['source']))
        else:
            logging.error(
                f'Try to setup with problem that is not in problem.json: {problem}'
            )
