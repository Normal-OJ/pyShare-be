from flask import Blueprint

from .utils import *
from .auth import *
from mongo import *

__all__ = ['notif_api']

notif_api = Blueprint('notif_api', __name__)

@notif_api.route('/', methods=['GET'])
@login_required
def get_notifs(user):
    notifs = [Notif(notif).to_dict() for notif in user.notifs]
    return HTTPResponse('success', data=notifs)
