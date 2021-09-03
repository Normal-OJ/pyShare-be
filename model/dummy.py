from flask import Blueprint
from mongo import *

__all__ = ['dummy_api']

dummy_api = Blueprint('dummy_api', __name__)