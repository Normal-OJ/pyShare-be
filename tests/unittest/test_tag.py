import pytest
from mongo import *
from mongo import Tag
from tests import utils


def test_tag_add():
    assert len(Tag.engine.objects(value='tag')) == 0
    Tag.add('tag')
    assert len(Tag.engine.objects(value='tag')) == 1


def test_tag_delete():
    t = Tag('tag')
    assert len(Tag.engine.objects(value='tag')) == 1

    t.delete()
    assert len(Tag.engine.objects(value='tag')) == 0


def test_tag_used_courses_count():
    t = Tag('tag')
    assert t.used_courses_count() == 0

    utils.course.lazy_add(tags=['tag'])
    assert t.used_courses_count() == 1
