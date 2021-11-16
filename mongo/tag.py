from . import engine
from .base import MongoBase

__all__ = ['Tag']


class Tag(MongoBase, engine=engine.Tag):
    def delete(self, category):
        '''
        Remove the tag
        '''
        if self.used_count(category) > 0:
            raise PermissionError('tag is used by others')\

        objects = None
        if category == engine.Tag.Category.COURSE:
            objects = engine.Course.objects(tags=self.value)
        if category == engine.Tag.Category.ATTACHMENT:
            objects = engine.Attachment.objects(tags=self.value)
        if category == engine.Tag.Category.NORMAL_PROBLEM:
            objects = engine.Problem.objects(tags=self.value,
                                             extra___cls='Normal')
        if category == engine.Tag.Category.OJ_PROBLEM:
            objects = engine.Problem.objects(tags=self.value, extra___cls='OJ')
        if objects is not None:
            objects.update(pull__tags=self.value)

        self.update(pull__categories=category)
        self.reload()
        if len(self.categories) == 0:
            self.obj.delete()

    def used_count(self, category):
        '''
        Return the number of resources use this tag
        '''
        if category == engine.Tag.Category.COURSE:
            return len(engine.Course.objects(tags=self.value))
        if category == engine.Tag.Category.ATTACHMENT:
            return len(engine.Attachment.objects(tags=self.value))
        if category == engine.Tag.Category.NORMAL_PROBLEM:
            return len(
                engine.Problem.objects(tags=self.value, extra___cls='Normal'))
        if category == engine.Tag.Category.OJ_PROBLEM:
            return len(
                engine.Problem.objects(tags=self.value, extra___cls='OJ'))

    def is_used(self, category):
        '''
        Check whether this tag is used by others
        '''
        return self.used_count(category) != 0

    @classmethod
    def add(cls, value, category):
        '''
        Add a tag to DB
        '''
        t = cls(value)
        if t is None:
            t = cls.engine(value=value).save()
        t.update(add_to_set=category)
        t.reload()
        return cls(t)

    @classmethod
    def is_tag(cls, value, category):
        return cls.engine(value=value, categories=category) is not None

    @classmethod
    def is_course_tag(cls, value):
        return cls.is_tag(value, engine.Tag.Category.COURSE)
