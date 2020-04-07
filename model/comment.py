from flask import Blueprint
from .utils import *
from .auth import *

__all__ = ['comment_api']

comment_api = Blueprint('comment_api', __name__)
COMMENT_DATA = [
    'target: str',
    'id: str',
    'title: str',
    'content: str',
    'code: str',
]


@comment_api.route('/', methods=['POST'])
@login_required
@Request.json(*COMMENT_DATA)
def create_comment(user, target, code, **ks):
    pass


@comment_api.route('/<_id>', methods=['GET'])
@login_required
def get_comment(user, _id):
    pass


@comment_api.route('/<_id>', methods=['PUT'])
@login_required
@Request.json(*COMMENT_DATA)
def modify_comment(user, _id):
    pass


@comment_api.route('/<_id>', methods=['DELETE'])
@login_required
def delete_comment(user, _id):
    pass


@comment_api.route('/<_id>/rejudge', methods=['GET'])
@login_required
def rejudge(user, _id):
    pass