from flask import Blueprint
from mongo import *
from mongo import engine
from .utils import *
from .auth import *

__all__ = ['user_api']

user_api = Blueprint('user', __name__)


@user_api.route('/', methods=['GET'])
def get_all_user():
    users = engine.User.objects
    # TODO: convert to MongoBase may cause unnecessary query
    users = [{
        'username': u.username,
        'displayName': u.display_name,
        'star': User(u.username).liked_amount(),
    } for u in users]
    return HTTPResponse('here you are.', data=users)


# TODO: statistic cause a lot of query, make a cache for better performance
@user_api.route('/<student>/statistic', methods=['GET'])
@Request.doc('student', 'student', User)
@login_required
def statistic(user, student):
    return HTTPResponse('here you are.', data=student.statistic())