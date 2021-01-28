from . import engine
from .base import MongoBase

__all__ = ['Tag']


class Tag(MongoBase, engine=engine.Tag):
    def delete(self):
        '''
        remove tag from problem if it have
        '''
        if self.used_courses() > 0:
            raise PermissionError('tag is used by others')
        # remove tag from course if it has
        engine.Course.objects(tags=self.value).update(pull__tags=self.value)
        # remove tag from problem if it has
        engine.Problem.objects(tags=self.value).update(pull__tags=self.value)
        self.obj.delete()

    def used_courses(self):
        '''
        check the tag is used by how many courses
        '''
        used_courses = engine.Course.objects(tags=self.value)
        return len(used_courses)

    @classmethod
    def add(cls, value):
        '''
        add a tag to db
        '''
        t = engine.Tag(value=value)
        t.save()
