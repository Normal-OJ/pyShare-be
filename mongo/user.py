from __future__ import annotations
from datetime import datetime, timedelta
from typing import (
    Container,
    Iterable,
    List,
    Optional,
    TYPE_CHECKING,
)
from hmac import compare_digest
from . import engine
from .utils import *
from .base import *
from .config import config
import jwt

__all__ = (
    'User',
    'jwt_decode',
)
JWT_EXP = timedelta(days=config['JWT']['EXP'])
JWT_ISS = config['JWT']['ISS']
JWT_SECRET = config['JWT']['SECRET']

if TYPE_CHECKING:
    from .problem import Problem
    from .comment import Comment


class User(MongoBase, engine=engine.User):
    class OJProblemResult(Enum):
        PASS = 0
        FAIL = 1
        NO_TRY = 2

    @classmethod
    def signup(
        cls,
        username: str,
        password: str,
        email: Optional[str] = None,
        course: Optional[str] = None,
        display_name: Optional[str] = None,
        school: Optional[str] = None,
        role: int = engine.User.Role.STUDENT,
    ):
        if len(password) == 0:
            raise ValueError('password cannot be empty')
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
            logger().warning(f'unknown role \'{role}\'')
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
        )

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
        full: bool = False,
    ):
        '''
        return user's statistic data in courses
        '''
        def include(course):
            return True if courses is None else course in courses

        def include_problem(problem):
            return problem.online and include(problem.course)

        def include_comment(comment):
            return all((
                comment.is_comment,
                comment.show,
                not comment.problem.is_OJ,
                include(comment.problem.course),
            ))

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
            'referenceCount': p.reference_count,
        } for p in filter(include_problem, self.problems)]
        # liked comments
        ret['likes'] = [{
            'id': c.id,
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
            'id': c.id,
            'course': {
                'name': c.problem.course.name,
                'id': c.problem.course.id
            },
            'pid': c.problem.pid,
            'floor': c.floor,
            'acceptance': c.acceptance,
        } for c in filter(include_comment, self.comments)]
        ret['replies'] = [{
            'id': c.id,
            'course': {
                'name': c.problem.course.name,
                'id': c.problem.course.id
            },
            'pid': c.problem.pid,
            'floor': c.floor,
        } for c in filter(include_reply, self.comments)]
        # comments be liked
        ret['liked'] = [{
            'id': c.id,
            'course': {
                'name': c.problem.course.name,
                'id': c.problem.course.id
            },
            'pid': c.problem.pid,
            'floor': c.floor,
            'starers': [u.info for u in c.liked],
        } for c in filter(include_comment, self.comments)
                        if full or len(c.liked)]
        # success & fail
        ret['execInfo'] = [{
            'id': c.id,
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

    def oj_statistic(self, problems: List['Problem']):
        '''
        Calculate a user's OJ problem statsitic data
        '''
        user_stat = {}
        ac_count = 0
        try_count = 0
        no_try_result = {
            'commentId': None,
            'result': self.OJProblemResult.NO_TRY,
            'tryCount': 0,
        }
        for problem in problems:
            problem_stat = {}
            try:
                comment = next(c for c in problem.comments if self == c.author)
            except StopIteration:
                problem_stat = no_try_result
            else:
                problem_stat = self.oj_comment_statistic(comment)
            finally:
                try_count += problem_stat['tryCount']
                ac_count += problem_stat['result'] == self.OJProblemResult.PASS
                user_stat[str(problem.pid)] = problem_stat
        return {
            'overview': {
                'acCount': ac_count,
                'tryCount': try_count,
            },
            **user_stat,
        }

    def oj_comment_statistic(self, comment: 'Comment'):
        stat = {'commentId': comment.id}
        if len(comment.submissions) == 0:
            stat['result'] = self.OJProblemResult.NO_TRY
        else:
            # Check whether there exists any AC submission
            result = self.OJProblemResult.NO_TRY
            for s in comment.submissions:
                judge_result = getattr(s.result, 'judge_result', -1)
                if judge_result == 0:
                    result = self.OJProblemResult.PASS
                    break
                elif judge_result != -1:
                    result = self.OJProblemResult.FAIL
            stat['result'] = result
        stat['tryCount'] = len(comment.submissions)
        return stat


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
