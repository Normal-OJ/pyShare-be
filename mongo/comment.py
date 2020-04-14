from . import engine
from .base import MongoBase
from .problem import Problem
from .user import User
from .utils import doc_required

__all__ = ['Comment']


class Comment(MongoBase, engine=engine.Comment):
    def __init__(self, _id):
        self.id = _id

    @doc_required('user', 'user', User)
    def permission(self, user: User, req):
        _permission = {'r'}
        if user == self.author:
            _permission.add('w')
            _permission.add('d')
        elif user > 'student':
            _permission.add('d')
        return bool(req & _permission)

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

    @classmethod
    def add_to_problem(
        cls,
        target,
        code,
        **ks,
    ):
        # directly submit
        if not isinstance(target, (Problem, engine.Problem)):
            # try convert to document
            target = Problem(target)
        # create new commment
        comment = cls.add(
            floor=problem.height + 1,
            depth=0,
            **ks,
        )
        # try create a submission
        # append to problem
        target.update(
            push__comments=comment,
            height__inc=1,
        )
        return comment

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
    ):
        # insert into DB
        comment = engine.Comment(
            title=title,
            content=content,
            author=author.obj,
            floor=floor,
            depth=depth,
        )
        comment.save()
        # append to author's
        author.update(push__comments=comment)
        return cls(comment.id)