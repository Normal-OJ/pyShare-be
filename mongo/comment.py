from __future__ import annotations
import enum
from . import engine
from .base import MongoBase
from .problem import Problem
from .course import Course
from .user import User
from .notif import Notif
from .utils import doc_required, get_redis_client
from .submission import *
from .event import (
    submission_completed,
    comment_created,
    reply_created,
    comment_liked,
    comment_unliked,
)

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
    __initialized = False

    class Permission(enum.Flag):
        READ = enum.auto()
        WRITE = enum.auto()
        DELETE = enum.auto()
        REJUDGE = enum.auto()
        UPDATE_STATE = enum.auto()

    def __new__(cls, pk, *args, **kwargs):
        if not cls.__initialized:
            submission_completed.connect(cls.on_submission_completed)
            cls.__initialized = True
        return super().__new__(cls, pk, *args, **kwargs)

    def __init__(self, _id):
        if isinstance(_id, self.engine):
            _id = _id.id
        self.id = _id

    @classmethod
    def on_submission_completed(cls, submission):
        if submission.comment is None:
            return
        comment = cls(submission.comment)
        comment.on_submission_completed_ins()

    @doc_required('user', User)
    def own_permission(self, user: User) -> 'Comment.Permission':
        c = Course(self.problem.course)
        _permission = self.Permission(0)
        # Author can edit, rejudge and delete comment
        if user == self.author:
            _permission |= ( \
                self.Permission.WRITE |
                self.Permission.REJUDGE |
                self.Permission.DELETE
            )
        # Course teacher can rejudge and delete comment
        elif c.permission(user=user, req=Course.Permission.WRITE):
            _permission |= (self.Permission.REJUDGE | self.Permission.DELETE)
        # Course teacher and admin can update state
        if user == c.teacher or user >= 'admin':
            _permission |= self.Permission.UPDATE_STATE
        # The comment is not deleted
        # and user can read problem
        if not self.hidden and Problem(self.problem).permission(
                user=user,
                req=Problem.Permission.READ,
        ):
            # Course teacher and admin can read
            if user == c.teacher or user >= 'admin':
                _permission |= self.Permission.READ
            # Otherwise, only author can see OJ comment
            elif self.problem.is_OJ:
                if user == self.author:
                    _permission |= self.Permission.READ
            else:
                _permission |= self.Permission.READ
        return _permission

    @doc_required('user', User)
    def permission(self, user: User, req: Comment.Permission) -> bool:
        _permission = self.own_permission(user=user)
        return bool(req & _permission)

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
        '''
        Like/Unlike a comment
        '''
        # unlike
        if user.obj in self.liked:
            action = 'pull'
            event = comment_unliked
        else:
            action = 'add_to_set'
            event = comment_liked
            # notify the author of the creation
            info = Notif.types.Like(
                comment=self.pk,
                liked=user.pk,
                problem=self.problem,
            )
            notif = Notif.new(info)
            self.author.update(push__notifs=notif.pk)
        self.update(**{f'{action}__liked': user.id})
        user.update(**{f'{action}__likes': self.id})
        self.reload()
        user.reload()
        event.send(self, user=user)

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

    def on_submission_completed_ins(self):
        if not self.is_comment:
            raise NotAComment
        from .submission import Submission
        self.reload('submissions')
        if self.submission is None:
            raise SubmissionNotFound
        if self.submission.result is None:
            return
        if self.submission.result.stderr:
            self.update(inc__fail=1)
        else:
            self.update(inc__success=1)
        # Process OJ problem
        if self.problem.is_OJ:
            is_ac = lambda s: s.result.judge_result == Submission.engine.JudgeResult.AC
            self.update(acceptance=self.Acceptance.ACCEPTED if any(
                map(is_ac, self.submissions)) else self.Acceptance.REJECTED)
        elif self.acceptance == self.Acceptance.NOT_TRY:
            self.update(acceptance=self.Acceptance.PENDING)

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
        redis = get_redis_client()
        # Ensure that comment field is sync with db
        with redis.lock(f'{author}-{target}'):
            target.reload('comments')
            # check if allow multiple comments
            if not target.allow_multiple_comments:
                comments = map(
                    lambda c: author == c.author,
                    filter(lambda c: c.show, target.comments),
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
                submission = comment.new_submission(code)
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
        comment_created.send(comment.reload())
        return comment

    def new_submission(self, code: str):
        '''
        Create submission attached to this comment
        '''
        # TODO: solve circular import between submission and comment
        from .submission import Submission
        if not self.is_comment:
            raise NotAComment
        submission = Submission.add(
            problem=self.problem,
            user=self.author,
            comment=self,
            code=code,
        )
        return submission

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
        reply_created.send(comment.reload())
        return comment

    @classmethod
    @doc_required('author', User)
    @doc_required('problem', Problem)
    def add(
        cls,
        title: str,
        content: str,
        author: User,
        floor: int,
        depth: int,
        problem: Problem,
    ):
        if not problem.permission(user=author, req=Problem.Permission.SUBMIT):
            raise PermissionError(f'{author} cannot submit to {problem}')
        comment = cls.engine(
            title=title,
            content=content,
            author=author.id,
            floor=floor,
            depth=depth,
            problem=problem.id,
        ).save()
        # append to author's
        author.update(push__comments=comment)
        return cls(comment)

    def add_new_submission(self, code):
        submission = self.new_submission(code)
        submission.submit()
        self.update(push__submissions=submission.obj)
        return submission
