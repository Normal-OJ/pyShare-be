from . import engine
from .base import MongoBase


class Comment(MongoBase, engine=engine.Comment):
    def __init__(self, _id):
        self.id = _id

    def delete(self):
        pass

    @classmethod
    def add(
        cls,
        target: 'Union[Problem, Comment]',
        code: str,
        **ks,
    ):
        pass