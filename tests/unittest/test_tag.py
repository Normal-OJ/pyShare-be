import pytest
import secrets
from mongo import Tag, engine
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def random_tag_str():
    return secrets.token_hex(8)


def test_tag_add():
    assert len(Tag.engine.objects(value='tag')) == 0
    t = Tag.add('tag', engine.Tag.Category.NORMAL_PROBLEM)
    assert Tag.is_tag('tag', engine.Tag.Category.NORMAL_PROBLEM)
    assert len(Tag.engine.objects(value='tag')) == 1, Tag.engine(
        value='tag', categories=engine.Tag.Category.NORMAL_PROBLEM).categories


def test_tag_delete():
    t = Tag.add('tag', engine.Tag.Category.NORMAL_PROBLEM)
    assert len(Tag.engine.objects(value='tag')) == 1
    t.delete(engine.Tag.Category.NORMAL_PROBLEM)
    assert len(Tag.engine.objects(value='tag')) == 0


def test_tag_used_courses_count():
    t = Tag.add('tag', engine.Tag.Category.COURSE)
    assert t.used_count(engine.Tag.Category.COURSE) == 0
    c = utils.course.lazy_add(tags=['tag'])
    assert t.used_count(engine.Tag.Category.COURSE) == 1
    c.patch_tag([], ['tag'], engine.Tag.Category.COURSE)
    assert t.used_count(engine.Tag.Category.COURSE) == 0


def test_cannot_delete_tag_used_by_course():
    tag = Tag.add(random_tag_str(), engine.Tag.Category.COURSE)
    course = utils.course.lazy_add(
        tags=[str(tag.pk)],
        auto_insert_tags=True,
    )
    with pytest.raises(
            PermissionError,
            match=r'.*used.*',
    ):
        tag.delete(engine.Tag.Category.COURSE)
