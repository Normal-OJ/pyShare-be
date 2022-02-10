import io
import secrets
from typing import Callable
from flask.testing import FlaskClient
import pytest
from mongo import Tag, engine
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
        Tag.add(tag, engine.Tag.Category.NORMAL_PROBLEM)
    teacher = utils.user.Factory.teacher()
    client = forge_client(teacher.username)
    rv = client.get('/tag')
    assert rv.status_code == 200
    rv_tags = rv.get_json()['data']
    sys_tags = [t.value for t in Tag.engine.objects]
    assert sorted(rv_tags) == sorted(sys_tags)


@pytest.mark.parametrize(
    ['lazy_add_key', 'category'],
    [
        ('tags', engine.Tag.Category.COURSE),
        ('normal_problem_tags', engine.Tag.Category.NORMAL_PROBLEM),
        ('OJ_problem_tags', engine.Tag.Category.OJ_PROBLEM),
    ],
)
def test_get_course_tags(
    forge_client: Callable[[str], FlaskClient],
    lazy_add_key: str,
    category: str,
):
    gen_tags = lambda: [random_tag_str() for _ in range(5)]
    keys = ('tags', 'normal_problem_tags', 'OJ_problem_tags')
    tags = {k: gen_tags() for k in keys}
    # Create course with some tags
    course = utils.course.lazy_add(
        auto_insert_tags=True,
        **tags,
    )
    client = forge_client(course.teacher.username)
    rv = client.get(
        '/tag',
        query_string=f'course={course.id}&category={category}',
    )
    assert rv.status_code == 200
    rv_tags = rv.get_json()['data']
    excepted = tags[lazy_add_key]
    assert sorted(rv_tags) == sorted(excepted)


def test_delete_tag(forge_client: Callable[[str], FlaskClient]):
    t = Tag.add(random_tag_str(), engine.Tag.Category.NORMAL_PROBLEM)
    user = utils.user.Factory.teacher()
    client = forge_client(user.username)
    rv = client.delete(
        '/tag',
        json={
            'tags': [str(t.pk)],
            'category': engine.Tag.Category.NORMAL_PROBLEM
        },
    )
    assert rv.status_code == 200, rv.data
    assert not Tag.is_tag(t.pk, engine.Tag.Category.NORMAL_PROBLEM)


def test_student_cannot_delete_tag(forge_client: Callable[[str], FlaskClient]):
    t = Tag.add(random_tag_str(), engine.Tag.Category.NORMAL_PROBLEM)
    user = utils.user.Factory.student()
    client = forge_client(user.username)
    rv = client.delete(
        '/tag',
        json={
            'tags': [str(t.pk)],
            'category': engine.Tag.Category.NORMAL_PROBLEM
        },
    )
    assert rv.status_code == 403, rv.data


def test_cannot_delete_tag_used_by_course(forge_client: Callable[[str],
                                                                 FlaskClient]):
    tag = random_tag_str()
    course = utils.course.lazy_add(
        tags=[tag],
        auto_insert_tags=True,
    )
    client = forge_client(course.teacher.username)
    rv = client.delete(
        '/tag',
        json={
            'tags': [tag],
            'category': engine.Tag.Category.COURSE
        },
    )
    assert rv.status_code == 400
    rv_data = rv.get_json()['data']
    fail = rv_data['fail']
    assert isinstance(fail, list) and len(fail) == 1
    assert 'used' in fail[0]['msg']
    assert fail[0]['value'] == tag


def test_cannot_delete_tag_used_by_attachment(
        forge_client: Callable[[str], FlaskClient]):
    tag = Tag.add(random_tag_str(), engine.Tag.Category.ATTACHMENT)
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
    rv = client.delete(
        '/tag',
        json={
            'tags': [str(tag.pk)],
            'category': engine.Tag.Category.ATTACHMENT
        },
    )
    assert rv.status_code == 400
    rv_data = rv.get_json()['data']
    fail = rv_data['fail']
    assert isinstance(fail, list) and len(fail) == 1
    assert 'used' in fail[0]['msg']
    assert fail[0]['value'] == str(tag.pk)
