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
]


class NotAComment(Exception):
    pass


class SubmissionNotFound(Exception):
    pass


class Comment(MongoBase, engine=engine.Comment):
    def __init__(self, _id):
        self.id = _id

    @doc_required('user', 'user', User)
    def permission(self, user: User, req):
        '''
        require 'j' for rejudge
        '''
        _permission = {'r'}
        if user == self.author:
            _permission |= {'w', 'j', 'd'}
        elif user > 'student':
            _permission |= {'d', 'j'}
        return bool(req & _permission)

    def to_dict(self):
        ret = self.to_mongo().to_dict()
        ret['created'] = self.created.timestamp()
        ret['updated'] = self.updated.timestamp()
        ret['submission'] = Submission(ret['submission']).to_dict()
        ret['author'] = User(ret['author']).info
        ret['replies'] = [str(r) for r in ret['replies']]
        ret['liked'] = [User(l).info for l in ret['liked']]
        for k in ('problem', 'passed', 'success', 'fail'):
            del ret[k]
        return ret

    def hidden(self):
        return self.status == 0

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
            action = 'push'
        self.update(**{f'{action}__liked': user.obj})
        user.update(**{f'{action}__likes': self.obj})

    def submit(self):
        if self.depth != 0:
            raise NotAComment
        submission = Submission(self.submission.id)
        # delete old submission
        if not submission:
            raise SubmissionNotFound
        code = submission.code
        submission.delete()
        # create a new one
        submission = Submission.add(
            problem=self.problem.obj,
            user=self.author.obj,
            code=code,
        )

    def finish_submission(self):
        '''
        called after a submission finish
        '''
        if self.depth != 0:
            raise NotAComment
        if not Submission(self.submission.id):
            raise SubmissionNotFound
        if self.submission.result.stderr:
            self.update(fail__inc=1)
        else:
            self.update(success__inc=1)

    @classmethod
    def add_to_problem(
        cls,
        target,
        code,
        author,
        **ks,
    ):
        # directly submit
        if not isinstance(target, (Problem, engine.Problem)):
            # try convert to document
            target = Problem(target)
        if isinstance(target, Problem):
            target = target.obj
        # create new commment
        comment = cls.add(
            floor=problem.height + 1,
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
        comment.update(submission=submission)
        # append to problem
        target.update(
            push__comments=comment,
            height__inc=1,
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
            floor=-1,
            depth=1,
            **ks,
        )
        target.update(push__replies=comment)
        return comment

    @classmethod
    @doc_required('author', 'author', User)
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
            author=author.obj,
            floor=floor,
            depth=depth,
            problem=problem,
        )
        comment.save()
        # append to author's
        author.update(push__comments=comment)
        return cls(comment.id)