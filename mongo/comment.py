from . import engine
from .base import MongoBase
from .problem import Problem
from .user import User
from .utils import doc_required
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
    def __init__(self, _id):
        self.id = str(_id)

    @doc_required('user', 'user', User)
    def permission(self, user: User, req):
        '''
        require 'j' for rejudge
        require 's' for changing state
        require 'd' for deletion
        require 'w' for writing
        require 'r' for reading
        '''
        _permission = {'r'}
        # author have all permissions except changing state
        if user == self.author:
            _permission |= {'w', 'j', 'd'}
            # can change state if he's a teacher
            if user > 'student':
                _permission |= {'s'}
        # teacher can not edit comment, but he can change state
        elif user > 'student' and self.problem.course in user.courses:
            _permission |= {'d', 'j', 's'}
        # other students can not view hidden comment
        elif self.hidden:
            _permission.remove('r')
        return bool(req & _permission)

    def to_dict(self):
        from .submission import Submission
        ret = self.to_mongo().to_dict()
        ret['created'] = self.created.timestamp()
        ret['updated'] = self.updated.timestamp()
        ret['submission'] = Submission(self.submission.id).to_dict()
        ret['submissions'] = [str(s.id) for s in self.submissions]
        ret['author'] = self.author.info
        ret['replies'] = [str(r) for r in ret['replies']]
        ret['liked'] = [l.info for l in self.liked]
        for k in (
                '_id',
                'problem',
                'passed',
                'success',
                'fail',
        ):
            if k in ret:
                del ret[k]
        return ret

    def delete(self):
        self.update(status=0)
        for reply in self.replies:
            reply.update(status=0)

    @doc_required('user', 'user', User)
    def like(self, user):
        # unlike
        if user.obj in self.liked:
            action = 'pull'
        else:
            action = 'add_to_set'
        self.update(**{f'{action}__liked': user.obj})
        user.update(**{f'{action}__likes': self.obj})
        # reload
        self.reload()
        # check pass
        if self.depth == 0 and user > 'student':
            for u in self.liked:
                if User(u.username) > 'student':
                    self.submission.update(passed=True)
                    return
            self.submission.update(passed=False)

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
    def add_to_problem(
        cls,
        target,
        code: str,
        author: str,
        **ks,
    ):
        # TODO: solve circular import between submission and comment
        from .submission import Submission
        # directly submit
        if not isinstance(target, (Problem, engine.Problem)):
            # try convert to document
            target = Problem(target)
        # check if allow multiple comments
        if not target.allow_multiple_comments:
            if any(comment.author.username == author
                   for comment in target.comments):
                raise TooManyComments

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
            problem=target.pk,
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
        return comment.reload()

    @classmethod
    def add_to_comment(
        cls,
        target,
        **ks,
    ):
        # reply other's comment
        if not isinstance(target, (cls, engine.Comment)):
            target = Comment(target)
        # create new comment
        comment = cls.add(
            floor=target.floor,
            depth=1,
            problem=target.problem,
            **ks,
        )
        target.update(push__replies=comment.obj)
        return comment

    @classmethod
    @doc_required('author', User)
    def add(
        cls,
        title: str,
        content: str,
        author: User,
        floor: int,
        depth: int,
        problem: engine.Problem = None,
    ):
        # insert into DB
        comment = engine.Comment(
            title=title,
            content=content,
            author=author.pk,
            floor=floor,
            depth=depth,
            problem=problem.pk if problem is not None else None,
        )
        comment.save()
        # append to author's
        author.update(push__comments=comment)
        return cls(comment.id)

    def add_new_submission(self, code):
        from .submission import Submission
        if not self.is_comment:
            raise NotAComment
        submission = Submission.add(
            problem=self.problem.pk,
            user=self.author.pk,
            comment=self.pk,
            code=code,
        )
        submission.submit()
        self.update(push__submissions=submission.obj)
        return submission
