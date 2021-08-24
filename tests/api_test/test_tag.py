from re import A
import secrets
from typing import Callable
from _pytest.mark import param
import pytest
from flask.testing import FlaskClient
from mongo import Tag
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def random_tag_str():
    return secrets.token_hex(8)


def test_add_tag(forge_client: Callable[[str], FlaskClient]):
    assert len(Tag.engine.objects) == 0
    tag_str = random_tag_str()
    teacher = utils.user.Factory.teacher()
    client = forge_client(teacher.username)
    rv = client.post(
        '/tag',
        json={'tags': [tag_str]},
    )
    assert rv.status_code == 200, rv.get_json()
    assert len(Tag.engine.objects) == 1
    assert Tag(tag_str)


def test_get_all_tag(forge_client: Callable[[str], FlaskClient]):
    tags = [random_tag_str() for _ in range(10)]
    for tag in tags:
        Tag.add(tag)
    teacher = utils.user.Factory.teacher()
    client = forge_client(teacher.username)
    rv = client.get('/tag')
    assert rv.status_code == 200
    rv_tags = rv.get_json()['data']
    sys_tags = [t.value for t in Tag.engine.objects]
    assert sorted(rv_tags) == sorted(sys_tags)


def test_get_course_tags(forge_client: Callable[[str], FlaskClient], ):
    tags = [random_tag_str() for _ in range(5)]
    # Create course with some tags
    course = utils.course.lazy_add(
        tags=tags,
        auto_insert_tags=True,
    )
    client = forge_client(course.teacher.username)
    rv = client.get(
        '/tag',
        query_string=f'course={course.id}',
    )
    assert rv.status_code == 200
    rv_tags = rv.get_json()['data']
    excepted = course.tags
    assert sorted(rv_tags) == sorted(excepted)
