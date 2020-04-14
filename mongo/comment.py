from . import engine
from .base import MongoBase
from .problem import Problem


class Comment(MongoBase, engine=engine.Comment):
    def __init__(self, _id):
        self.id = _id

    def delete(self):
        self.status = 0
        for reply in self.replies:
            reply.update(status=0)
        self.save()

    @classmethod
    def add_to_problem(
        cls,
        target,
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
    def add(
        cls,
        title: str,
        content: str,
        author,
        floor: int,
        depth: int,
    ):
        # insert into DB
        comment = engine.Comment(
            title=title,
            content=content,
            author=author,
            floor=floor,
            depth=depth,
        )
        comment.save()
        return cls(comment.id)