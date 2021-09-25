import secrets
from mongo import Tag
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def random_tag_str():
    return secrets.token_hex(8)


def test_tag_add():
    assert len(Tag.engine.objects(value='tag')) == 0
    Tag.add('tag')
    assert len(Tag.engine.objects(value='tag')) == 1


def test_tag_delete():
    t = Tag.add('tag')
    assert len(Tag.engine.objects(value='tag')) == 1
    t.delete()
    assert len(Tag.engine.objects(value='tag')) == 0


def test_tag_used_courses_count():
    t = Tag.add('tag')
    assert t.used_count() == 0
    c = utils.course.lazy_add(tags=['tag'])
    assert t.used_count() == 1
    c.patch_tag([], ['tag'])
    assert t.used_count() == 0


def test_delete_tag_used_by_course():
    tag_str = random_tag_str()
    tag = Tag.add(tag_str)
