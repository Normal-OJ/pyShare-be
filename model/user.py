from flask import Blueprint
from mongo import *
from mongo import engine

__all__ = ['user_api']

user_api = Blueprint('user', __name__)


@user_api.route('/')
def get_all_user():
    users = engine.User.objects
    users = [{
        'username': u.username,
        'displayName': u.display_name,
        'star': u.star,
    } for u in users]
    return HTTPResponse('here you are.', data=users)
