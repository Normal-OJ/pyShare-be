from . import engine
from .base import MongoBase

__all__ = ['Tag']


class Tag(MongoBase, engine=engine.Tag):
    def __init__(self, value):
        self.value = value

    def delete(self):
        '''
        remove tag from problem if it have
        '''
        # remove tag from problem if it have
        engine.Problem.objects(tags=self.value).update(pull__tags=self.value)
        self.obj.delete()

    @classmethod
    def add(value):
        '''
        add a tag to db
        '''
        t = engine.Tag(value)
        t.save()
