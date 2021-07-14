from datetime import datetime, timedelta
from typing import Container, Iterable, Optional
from hmac import compare_digest

from . import engine
from .utils import *
from .base import *

import jwt
import os

__all__ = ['User', 'jwt_decode']

JWT_EXP = timedelta(days=int(os.getenv('JWT_EXP', '30')))
JWT_ISS = os.getenv('JWT_ISS', 'test.test')
JWT_SECRET = os.getenv('JWT_SECRET', 'SuperSecretString')


class User(MongoBase, engine=engine.User):
    @classmethod
    def signup(
        cls,
        username,
        password,
        email=None,
        course=None,
        display_name=None,
        school=None,
        role=2,
    ):
        user_id = hash_id(username, password)
        if email is not None:
            email = cls.formated_email(email)
        user = cls.engine(
            username=username,
            user_id=user_id,
            user_id2=user_id,
            display_name=display_name or username,
            email=email,
            school=school or '',
            role=role,
        ).save(force_insert=True)
        user = cls(user)
        # add user to course
        if course is not None:
            from .course import Course
            Course(course).add_student(user)
        return user.reload()

    @classmethod
    def formated_email(cls, email: str):
        return email.lower().strip()

    @classmethod
    def login(
        cls,
        school,
        username,
        password,
    ):
        # try to get a user by given info
        user = cls.engine.objects.get(
            username=username,
            school=school,
        )
        # calculate user hash
        user_id = hash_id(user.username, password)
        if compare_digest(user.user_id, user_id) or \
            compare_digest(user.user_id2, user_id):
            return cls(user)
        raise engine.DoesNotExist

    @classmethod
    def login_by_email(cls, email: str, password: str):
        user = cls.get_by_email(email)
        user_id = hash_id(user.username, password)
        if compare_digest(user.user_id, user_id) or \
            compare_digest(user.user_id2, user_id):
            return user
        raise engine.DoesNotExist

    @classmethod
    def get_by_username(
        cls,
        username: str,
        school: str = '',
    ):
        obj = cls.engine.objects.get(
            username=username,
            school=school,
        )
        return cls(obj)

    @classmethod
    def get_by_email(cls, email: str):
        if email is None:
            raise engine.DoesNotExist
        obj = cls.engine.objects.get(email=cls.formated_email(email))
        return cls(obj)

    @property
    def cookie(
        self,
        keys: Optional[Iterable[str]] = None,
    ):
        WHITELIST = {
            '_id',
            'username',
            'email',
            'displayName',
            'md5',
            'role',
            'courses',
            'school',
            'problems',
            'comments',
            'likes',
            'notifs',
        }
        if keys is None:
            keys = [
                '_id',
                'username',
                'email',
                'displayName',
                'md5',
                'role',
                'courses',
            ]
        if any(key not in WHITELIST for key in keys):
            raise ValueError('Unallowed key found')
        return self.jwt(*keys)

    @property
    def secret(self):
        keys = [
            '_id',
            'username',
            'userId',
        ]
        return self.jwt(*keys, secret=True)

    @property
    def role_ids(self):
        return {
            'admin': 0,
            'teacher': 1,
            'student': 2,
        }

    def get_role_id(self, role):
        try:
            return self.role_ids[role]
        except KeyError:
            self.logger.warning(f'unknown role \'{role}\'')
            return None

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
            self > 'student' will be True
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

    def jwt(self, *keys, secret=False, **kwargs):
        if not self:
            return ''
        user = self.reload().to_mongo()
        data = {k: user.get(k) for k in keys}
        data.update(kwargs)
        payload = {
            'iss': JWT_ISS,
            'exp': datetime.now() + JWT_EXP,
            'secret': secret,
            'data': data
        }
        return jwt.encode(
            payload,
            JWT_SECRET,
            algorithm='HS256',
            json_encoder=ObjectIdEncoder,
        ).decode()

    def change_password(self, password):
        user_id = hash_id(self.username, password)
        self.update(user_id=user_id, user_id2=user_id)
        self.reload()

    def add_submission(self, submission: engine.Submission):
        if submission.result.stderr:
            self.update(inc__fail=1)
        else:
            self.update(inc__success=1)

    def liked_amount(self):
        return sum(len(c.liked) for c in self.comments)

    def statistic(
        self,
        courses: Optional[Container[engine.Course]] = None,
    ):
        '''
        return user's statistic data in courses
        '''
        def include(course):
            return True if courses is None else course in courses

        def include_problem(problem):
            return problem.online and include(problem.course)

        def include_comment(comment):
            return comment.is_comment and comment.show and include(
                comment.problem.course)

        def include_reply(reply):
            return not reply.is_comment and reply.show and include(
                reply.problem.course)

        ret = {}
        # all problems
        ret['problems'] = [{
            'course': {
                'name': p.course.name,
                'id': p.course.id
            },
            'pid': p.pid,
        } for p in filter(include_problem, self.problems)]
        # liked comments
        ret['likes'] = [{
            'course': {
                'name': c.problem.course.name,
                'id': c.problem.course.id
            },
            'pid': c.problem.pid,
            'floor': c.floor,
            'staree': c.author.info,
        } for c in filter(include_comment, self.likes)]
        # comments
        ret['comments'] = [{
            'course': {
                'name': c.problem.course.name,
                'id': c.problem.course.id
            },
            'pid': c.problem.pid,
            'floor': c.floor,
            'accepted': c.has_accepted,
        } for c in filter(include_comment, self.comments)]
        ret['replies'] = [{
            'course': {
                'name': c.problem.course.name,
                'id': c.problem.course.id
            },
            'pid': c.problem.pid,
            'floor': c.floor,
        } for c in filter(include_reply, self.comments)]
        # comments be liked
        ret['liked'] = [{
            'course': {
                'name': c.problem.course.name,
                'id': c.problem.course.id
            },
            'pid': c.problem.pid,
            'floor': c.floor,
            'starers': [u.info for u in c.liked],
        } for c in filter(include_comment, self.comments)]
        # success & fail
        ret['execInfo'] = [{
            'course': {
                'name': c.problem.course.name,
                'id': c.problem.course.id
            },
            'pid': c.problem.pid,
            'floor': c.floor,
            'success': c.success,
            'fail': c.fail,
        } for c in filter(include_comment, self.comments)]
        return ret


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
