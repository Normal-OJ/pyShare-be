from flask import Blueprint
from mongo import *
from mongo import engine
from .utils import *
from .auth import *

__all__ = ['user_api']

user_api = Blueprint('user', __name__)


@user_api.route('/', methods=['GET'])
@login_required
def get_all_user():
    users = engine.User.objects
    users = [{
        **u.info,
    } for u in map(User, users)]
    return HTTPResponse('here you are.', data=users)


@user_api.route('/<the_user>', methods=['GET'])
@Request.doc('the_user', 'the_user', User)
@login_required
def get_user(user, the_user):
    return HTTPResponse('here you are.', data=the_user.info)


# TODO: statistic cause a lot of query, make a cache for better performance
@user_api.route('/<student>/statistic', methods=['GET'])
@Request.doc('student', 'student', User)
@login_required
def statistic(user, student):
    return HTTPResponse('here you are.', data=student.statistic())