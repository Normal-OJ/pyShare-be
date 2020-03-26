from datetime import datetime, timedelta
from hmac import compare_digest
from flask import current_app

from . import engine
from .utils import *
from .base import *

import base64
import hashlib
import html
import json as jsonlib
import jwt
import os

__all__ = ['User', 'jwt_decode']

JWT_EXP = timedelta(days=int(os.getenv('JWT_EXP', '30')))
JWT_ISS = os.getenv('JWT_ISS', 'test.test')
JWT_SECRET = os.getenv('JWT_SECRET', 'SuperSecretString')


class User(MongoBase, engine=engine.User):
    def __init__(self, username):
        self.username = username

    @classmethod
    def signup(cls, username, password, email):
        user = cls(username)
        user_id = hash_id(user.username, password)
        cls.engine(
            user_id=user_id,
            user_id2=user_id,
            username=user.username,
            email=email,
            md5=hashlib.md5(email.strip().encode()).hexdigest(),
            active=False,
        ).save(force_insert=True)
        return user.reload()

    @classmethod
    def login(cls, username, password):
        try:
            user = cls.get_by_username(username)
        except engine.DoesNotExist:
            user = cls.get_by_email(username)
        user_id = hash_id(user.username, password)
        if compare_digest(user.user_id, user_id) or compare_digest(
                user.user_id2, user_id):
            return user
        raise engine.DoesNotExist

    @classmethod
    def get_by_username(cls, username):
        obj = cls.engine.objects.get(username=username)
        return cls(obj.username)

    @classmethod
    def get_by_email(cls, email):
        obj = cls.engine.objects.get(email=email)
        return cls(obj.username)

    @property
    def cookie(self):
        keys = [
            'username',
            'email',
            'displayName',
            'md5',
            'active',
            'role',
        ]
        return self.jwt(*keys)

    @property
    def secret(self):
        keys = ['username', 'userId']
        return self.jwt(*keys, secret=True)

    @property
    def info(self):
        return {
            'username': self.username,
            'displayedName': self.profile.displayed_name,
            'md5': self.md5
        }

    @property
    def role_ids(self):
        return {
            'admin': 0,
            'teacher': 1,
            'student': 2,
        }

    def get_role_id(self, role):
        _role = self.role_ids.get(role)
        if _role is None:
            self.logger.warning(f'unknown role \'{role}\'')
        return _role

    def __eq__(self, other):
        # whether the user is the role?
        if isinstance(other, str):
            return self.get_role_id(other) == self.role
        return super().__eq__(other)

    def __gt__(self, value):
        '''
        check whether the user has a role super than `value` (string)
        e.g.
            if self is a admin
            self < 'student' will be True
        '''
        # only support compare to string
        if not isinstance(value, str):
            return False
        role = self.get_role_id(value)
        # compare to unknown role always return `False`
        if role is None:
            return False
        # the less id means more permission
        return self.role < role

    def __ge__(self, value):
        return self > value or self == value

    def __lt__(self, value):
        return not self >= value

    def __le__(self, value):
        return not self > value

    def is_role(self, *roles):
        '''
        is this user belonging one of the required roles?
        '''
        roles = {r: self.get_role_id(r) for r in role}
        return self.role in roles

    def jwt(self, *keys, secret=False, **kwargs):
        if not self:
            return ''
        user = self.reload().to_mongo()
        user['username'] = user.get('_id')
        data = {k: user.get(k) for k in keys}
        data.update(kwargs)
        payload = {
            'iss': JWT_ISS,
            'exp': datetime.now() + JWT_EXP,
            'secret': secret,
            'data': data
        }
        return jwt.encode(payload, JWT_SECRET, algorithm='HS256').decode()

    def change_password(self, password):
        user_id = hash_id(self.username, password)
        self.update(user_id=user_id, user_id2=user_id)
        self.reload()

    def add_submission(self, submission: engine.Submission):
        if submission.score == 100:
            if submission.problem_id not in self.AC_problem_ids:
                self.AC_problem_ids.append(submission.problem_id)
            self.AC_submission += 1
        self.submission += 1
        self.save()


def jwt_decode(token):
    try:
        json = jwt.decode(
            token,
            JWT_SECRET,
            issuer=JWT_ISS,
            algorithms='HS256',
        )
    except jwt.exceptions.PyJWTError:
        return None
    return json
