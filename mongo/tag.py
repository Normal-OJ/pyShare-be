from . import engine
from .base import MongoBase

__all__ = ['Tag']


class Tag(MongoBase, engine=engine.Tag):
    def delete(self):
        '''
        Remove the tag
        '''
        if self.used_count() > 0:
            raise PermissionError('tag is used by others')
        # remove tag from course if it has
        engine.Course.objects(tags=self.value).update(pull__tags=self.value)
        # remove tag from problem if it has
        engine.Problem.objects(tags=self.value).update(pull__tags=self.value)
        self.obj.delete()

    def used_count(self):
        '''
        Return the number of resources use this tag
        '''
        used_courses_count = engine.Course.objects(tags=self.value)
        return len(used_courses_count)

    def is_used(self):
        '''
        Check whether this tag is used by others
        '''
        return self.used_count() != 0

    @classmethod
    def add(cls, value):
        '''
        Add a tag to DB
        '''
        t = cls.engine(value=value).save()
        return cls(t)
