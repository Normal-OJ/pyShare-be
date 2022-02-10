import itertools
from typing import List

from . import engine
from .course import Course
from .base import MongoBase
from .utils import doc_required

__all__ = ['Tag']


class Tag(MongoBase, engine=engine.Tag):
    def delete(self, category):
        '''
        Remove the tag
        '''
        if self.used_count(category) > 0:
            raise PermissionError('tag is used by others')

        objects = None
        if category == engine.Tag.Category.COURSE:
            objects = engine.Course.objects(tags=self.value)
        if category == engine.Tag.Category.ATTACHMENT:
            objects = engine.Attachment.objects(tags=self.value)
        if category == engine.Tag.Category.NORMAL_PROBLEM:
            objects = engine.Problem.objects(
                tags=self.value,
                __raw__={'extra': {
                    '_cls': 'Normal'
                }},
            )
        if category == engine.Tag.Category.OJ_PROBLEM:
            objects = engine.Problem.objects(
                tags=self.value,
                __raw__={'extra': {
                    '_cls': 'OJ'
                }},
            )
        if objects is not None:
            objects.update(pull__tags=self.value)
        else:
            raise ValueError('category not exist')

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
                engine.Problem.objects(
                    tags=self.value,
                    __raw__={'extra': {
                        '_cls': 'Normal'
                    }},
                ))
        if category == engine.Tag.Category.OJ_PROBLEM:
            return len(
                engine.Problem.objects(
                    tags=self.value,
                    __raw__={'extra': {
                        '_cls': 'OJ'
                    }},
                ))

        raise ValueError('category not exist')

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
        if not t:
            t = cls.engine(value=value).save()
        t.update(add_to_set__categories=category)
        t.reload()
        return cls(t)

    @classmethod
    def is_tag(cls, value, category):
        return len(cls.engine.objects(value=value, categories=category)) > 0

    @classmethod
    def is_course_tag(cls, value):
        return cls.is_tag(value, engine.Tag.Category.COURSE)

    @classmethod
    @doc_required('course', Course, null=True)
    def filter(
        cls,
        course: Course,
        category: int,
    ) -> List[str]:
        if course is not None:
            return course.get_tags_by_category(category)
        return [t.value for t in cls.engine.objects(categories=category)]
