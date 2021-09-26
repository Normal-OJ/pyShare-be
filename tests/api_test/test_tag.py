import io
import secrets
from typing import Callable
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


def test_delete_tag(forge_client: Callable[[str], FlaskClient]):
    t = Tag.add(random_tag_str())
    user = utils.user.Factory.teacher()
    client = forge_client(user.username)
    rv = client.delete('/tag', json={'tags': [str(t.pk)]})
    assert rv.status_code == 200, rv.data
    assert not Tag(t.pk)


def test_student_cannot_delete_tag(forge_client: Callable[[str], FlaskClient]):
    t = Tag.add(random_tag_str())
    user = utils.user.Factory.student()
    client = forge_client(user.username)
    rv = client.delete('/tag', json={'tags': [str(t.pk)]})
    assert rv.status_code == 403, rv.data


def test_cannot_delete_tag_used_by_course(forge_client: Callable[[str],
                                                                 FlaskClient]):
    tag = random_tag_str()
    course = utils.course.lazy_add(
        tags=[tag],
        auto_insert_tags=True,
    )
    client = forge_client(course.teacher.username)
    rv = client.delete('/tag', json={'tags': [tag]})
    assert rv.status_code == 400
    rv_data = rv.get_json()['data']
    fail = rv_data['fail']
    assert isinstance(fail, list) and len(fail) == 1
    assert 'used' in fail[0]['msg']
    assert fail[0]['value'] == tag


def test_cannot_delete_tag_used_by_attachment(
        forge_client: Callable[[str], FlaskClient]):
    tag = Tag.add(random_tag_str())
    user = utils.user.Factory.admin()
    # Create attachment with tag
    client = forge_client(user.username)
    rv = client.post(
        '/attachment',
        data={
            'filename': 'test',
            'description': 'test',
            'fileObj': (io.BytesIO(b'test'), 'test'),
            'patchNote': '',
            'tags': str(tag.pk),
        },
    )
    assert rv.status_code == 200, rv.data
    rv = client.delete('/tag', json={'tags': [str(tag.pk)]})
    assert rv.status_code == 400
    rv_data = rv.get_json()['data']
    fail = rv_data['fail']
    assert isinstance(fail, list) and len(fail) == 1
    assert 'used' in fail[0]['msg']
    assert fail[0]['value'] == str(tag.pk)
