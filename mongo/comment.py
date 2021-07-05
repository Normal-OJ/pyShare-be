from enum import Enum
from . import engine
from .base import MongoBase
from .problem import Problem
from .course import Course
from .user import User
from .notif import Notif
from .utils import doc_required, get_redis_client
from .submission import *

__all__ = [
    'Comment',
    'NotAComment',
    'SubmissionNotFound',
    'TooManyComments',
]


class NotAComment(Exception):
    pass


class SubmissionNotFound(Exception):
    pass


class TooManyComments(Exception):
    pass


class Comment(MongoBase, engine=engine.Comment):
    class Permission(Enum):
        READ = 'r'
        WRITE = 'w'
        DELETE = 'd'
        REJUDGE = 'j'
        UPDATE_STATE = 's'

    def __init__(self, _id):
        if isinstance(_id, self.engine):
            _id = _id.id
        self.id = _id

    @doc_required('user', 'user', User)
    def own_permission(self, user: User):
        '''
        require 'j' for rejudge
        require 's' for changing state
        require 'd' for deletion
        require 'w' for writing
        require 'r' for reading
        '''
        c = Course(self.problem.course)
        _permission = set()
        # Author can edit, rejudge and delete comment
        if user == self.author:
            _permission |= {*'wjd'}
        # Course teacher can rejudge and delete comment
        elif user == c.teacher:
            _permission |= {*'jd'}
        # Course teacher and admin can update state
        if user == c.teacher or user >= 'admin':
            _permission.add('s')
        # The comment is not deleted
        # and user can read problem
        if not self.hidden and Problem(self.problem).permission(
                user=user,
                req={'r'},
        ):
            # Course teacher and admin can read
            if user == c.teacher or user >= 'admin':
                _permission.add('r')
            # Otherwise, only author can see OJ comment
            elif self.problem.is_OJ:
                if user == self.author:
                    _permission.add('r')
            else:
                _permission.add('r')
        return _permission

    @doc_required('user', 'user', User)
    def permission(self, user: User, req):
        _permission = self.own_permission(user=user)
        if isinstance(req, set):
            return not bool(req - _permission)
        return req in _permission

    def to_dict(self):
        from .submission import Submission
        ret = self.to_mongo().to_dict()
        ret['created'] = self.created.timestamp()
        ret['updated'] = self.updated.timestamp()
        ret['submission'] = self.submission and Submission(
            self.submission).to_dict()
        ret['submissions'] = [s.pk for s in self.submissions]
        ret['author'] = self.author.info
        ret['replies'] = [str(r) for r in ret['replies']]
        ret['liked'] = [l.info for l in self.liked]
        for k in (
                '_id',
                'problem',
                'success',
                'fail',
        ):
            if k in ret:
                del ret[k]
        return ret

    def delete(self):
        self.update(status=self.engine.Status.HIDDEN)
        for reply in self.replies:
            reply.update(status=self.engine.Status.HIDDEN)
        return self

    @doc_required('user', 'user', User)
    def like(self, user):
        # unlike
        if user.obj in self.liked:
            action = 'pull'
        else:
            action = 'add_to_set'
            # notify the author of the creation
            info = Notif.types.Like(
                comment=self.pk,
                liked=user.pk,
                problem=self.problem,
            )
            notif = Notif.new(info)
            self.author.update(push__notifs=notif.pk)
        self.update(**{f'{action}__liked': user.obj})
        user.update(**{f'{action}__likes': self.obj})
        # reload
        self.reload()

    def submit(self, code=None):
        '''
        rejudge current submission
        '''
        from .submission import Submission
        if not self.is_comment:
            raise NotAComment
        submission = Submission(self.submission.id)
        if not submission:
            raise SubmissionNotFound
        # delete old submission
        submission.clear()
        if code is not None:
            submission.update(code=code)
        submission.submit()

    def finish_submission(self):
        '''
        called after a submission finish
        '''
        from .submission import Submission
        if not self.is_comment:
            raise NotAComment
        if not Submission(self.submission.id):
            raise SubmissionNotFound
        if self.submission.result.stderr:
            self.update(inc__fail=1)
        else:
            self.update(inc__success=1)

    @classmethod
    @doc_required('author', User)
    @doc_required('target', Problem)
    def add_to_problem(
        cls,
        target: Problem,
        code: str,
        author: User,
        **ks,
    ):
        # TODO: solve circular import between submission and comment
        from .submission import Submission
        redis = get_redis_client()
        # Ensure that comment field is sync with db
        with redis.lock(f'{author}-{target}'):
            target.reload('comments')
            # check if allow multiple comments
            if not target.allow_multiple_comments:
                comments = map(
                    lambda c: author == c.author,
                    filter(
                        lambda c: c.status == engine.Comment.Status.SHOW,
                        target.comments,
                    ),
                )
                if any(comments):
                    raise TooManyComments
            # Ensure the height field is correct
            with redis.lock(str(target)):
                target.reload('height')
                # create new commment
                comment = cls.add(
                    floor=target.height + 1,
                    depth=0,
                    author=author,
                    problem=target,
                    **ks,
                )
                # try create a submission
                submission = Submission.add(
                    problem=target,
                    user=author,
                    comment=comment,
                    code=code,
                )
                submission.submit()
                comment.update(push__submissions=submission.obj)
                # append to problem
                target.update(
                    push__comments=comment.obj,
                    inc__height=1,
                )
        # notify relevant user
        info = Notif.types.NewComment(problem=target.pk)
        if target.author != comment.author:
            notif = Notif.new(info)
            target.author.update(push__notifs=notif.pk)
        return comment.reload()

    @classmethod
    def add_to_comment(
        cls,
        target,
        **ks,
    ):
        '''
        add a comment to reply other's comment
        '''
        target = Comment(target)
        if not target:
            raise engine.DoesNotExist
        # create new comment
        comment = cls.add(
            floor=target.floor,
            depth=1,
            problem=target.problem,
            **ks,
        )
        target.update(push__replies=comment.obj)
        # notify relevant users
        info = Notif.types.NewReply(
            comment=target.pk,
            problem=target.problem,
        )
        authors = {target.author, target.problem.author} - {
            comment.author,
        }
        if authors:
            notif = Notif.new(info)
        for author in authors:
            author.update(push__notifs=notif.pk)
        return comment.reload()

    @classmethod
    @doc_required('author', User)
    def add(
        cls,
        title: str,
        content: str,
        author: User,
        floor: int,
        depth: int,
        problem: engine.Problem,
    ):
        # check permission
        if not Problem(problem.pk).permission(user=author, req={
                'r'
        }) or not Course(problem.course.pk).permission(user=author, req={'p'}):
            raise PermissionError('Not enough permission')
        # insert into DB
        comment = cls.engine(
            title=title,
            content=content,
            author=author.pk,
            floor=floor,
            depth=depth,
            problem=problem.pk,
        ).save()
        # append to author's
        author.update(push__comments=comment)
        return cls(comment)

    def add_new_submission(self, code):
        from .submission import Submission
        if not self.is_comment:
            raise NotAComment
        submission = Submission.add(
            problem=self.problem,
            user=self.author,
            comment=self,
            code=code,
        )
        submission.submit()
        self.update(push__submissions=submission.obj)
        return submission
