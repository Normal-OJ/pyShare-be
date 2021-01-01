from . import engine
from .base import MongoBase

__all__ = ['Tag']


class Tag(MongoBase, engine=engine.Tag):
    def delete(self):
        '''
        remove tag from problem if it have
        '''
        # remove tag from course if it has
        engine.Course.objects(tags=self.value).update(pull__tags=self.value)
        # remove tag from problem if it has
        engine.Problem.objects(tags=self.value).update(pull__tags=self.value)
        self.obj.delete()

    @classmethod
    def add(cls, value):
        '''
        add a tag to db
        '''
        t = engine.Tag(value=value)
        t.save()
