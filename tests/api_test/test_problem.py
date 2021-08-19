from typing import Callable, Optional
from flask.testing import FlaskClient
import pytest
from tests.base_tester import BaseTester
from mongo import *
from mongo import engine
import io
import mongomock.gridfs
import threading
import concurrent.futures
from tests import utils

mongomock.gridfs.enable_gridfs_integration()


def get_file(file):
    with open("./tests/problem_test_case/" + file, 'rb') as f:
        return {'case': (io.BytesIO(f.read()), "test_case.zip")}


class TestProblem(BaseTester):
    def test_get_problems(
        self,
        forge_client: Callable[[str, Optional[str]], FlaskClient],
        config_app,
    ):
        # There exists 3 problem in test env
        config_app(env='test')
        # Get problems
        client = forge_client('teacher1')
        rv = client.get('/problem?offset=0&count=-1')
        json = rv.get_json()
        assert rv.status_code == 200, (rv, client.cookie_jar)
        assert len(json['data']) == 3, json

    def test_get_permission(self, forge_client, config_app):
        config_app(env='test')
        client = forge_client('teacher1')

        rv = client.get(f'/problem/1/permission')
        json = rv.get_json()
        assert rv.status_code == 200
        assert set(json['data']) == {*'rwdcj'}

    def test_create_problem(
        self,
        forge_client: Callable[[str, Optional[str]], FlaskClient],
        config_app,
    ):
        config_app(env='test')
        client = forge_client('teacher1')
        # Create a new problem
        rv = client.post(
            '/problem',
            json={
                'title': 'test',
                'description': '',
                'tags': [],
                'course': str(Course.get_by_name('course_108-1').id),
                'defaultCode': '',
                'status': 1,
                'isTemplate': False,
                'allowMultipleComments': True,
            },
        )
        json = rv.get_json()
        assert rv.status_code == 200, json
        assert len(engine.Problem.objects) == 4

    def test_cannot_read_deleted_comment_in_problem(
        self,
        forge_client: Callable[[str, Optional[str]], FlaskClient],
    ):
        # Create some comments
        problem = utils.problem.lazy_add(allow_multiple_comments=True)
        user = problem.author
        cs = [
            utils.comment.lazy_add_comment(
                author=user,
                problem=problem,
            ) for _ in range(10)
        ]
        # TODO: move positive validation to another testcase
        client = forge_client(user.username)
        rv = client.get(f'/problem/{problem.pid}')
        rv_json = rv.get_json()
        assert rv.status_code == 200, rv_json
        assert len(rv_json['data']['comments']) == len(cs)
        # Delete some
        for c in cs[:len(cs) // 2]:
            c.delete()
        rv = client.get(f'/problem/{problem.pid}')
        rv_json = rv.get_json()
        assert rv.status_code == 200, rv_json
        assert len(rv_json['data']['comments']) == len(cs) - len(cs) // 2

    def test_copy(
        self,
        forge_client: Callable[[str, Optional[str]], FlaskClient],
        config_app,
    ):
        config_app(env='test')
        client = forge_client('teacher1')

        rv = client.get(
            f'/problem/2/clone/{str(Course.get_by_name("course_108-1").id)}')
        json = rv.get_json()
        assert rv.status_code == 200, json

        rv = client.get('/problem?title=p2')
        json = rv.get_json()
        assert rv.status_code == 200
        assert len(json['data']) == 2

    def test_rejudge(
        self,
        forge_client: Callable[[str, Optional[str]], FlaskClient],
    ):
        # TODO: see if comments are rejudged or not
        teacher = utils.user.Factory.teacher()
        course = utils.course.lazy_add(teacher=teacher)
        problem = utils.problem.lazy_add(course=course)
        utils.comment.lazy_add_comment(
            author=teacher.pk,
            problem=problem,
        )
        client = forge_client(teacher.username)

        rv = client.get(f'/problem/{problem.id}/rejudge')
        json = rv.get_json()
        assert rv.status_code == 200, json


class TestAttachment(BaseTester):
    @pytest.mark.parametrize('key, value, status_code, message', [
        ('attachmentId', None, 200, 'your file'),
        (None, None, 200, 'db file'),
        ('attachmentName', None, 400, None),
        ('attachmentName', 'att', 400, None),
        ('attachmentId', 'a' * 24, 404, None),
    ])
    def test_add_attachment(self, forge_client, config_app, key, value,
                            status_code, message):
        config_app(env='test')
        client = forge_client('teacher1')
        rv = client.get('/attachment')
        id = rv.get_json()['data'][0]['id']

        data = {
            'attachment': (io.BytesIO(b'Win'), 'goal'),
            'attachmentName': 'haha',
            'attachmentId': id,
        }
        if key:
            if not isinstance(key, list):
                key = [key]
                value = [value]
            for i in range(len(key)):
                if value[i] is None:
                    del data[key[i]]
                else:
                    data[key[i]] = value[i]

        quote_count = 0
        if status_code == 200 and 'attachmentId' in data:
            rv = client.get(f'/attachment/{data["attachmentId"]}/meta')
            quote_count = rv.get_json()['data']['quoteCount']

        rv = client.post('/problem/1/attachment', data=data)
        assert rv.status_code == status_code, rv.get_json()

        if message:
            assert message in rv.get_json()['message']

        if status_code == 200:
            rv = client.get(f'/problem/1/attachment/{data["attachmentName"]}')
            assert rv.status_code == 200

            if 'attachmentId' in data:
                rv = client.get(f'/attachment/{data["attachmentId"]}/meta')
                assert rv.status_code == 200
                assert rv.get_json()['data']['quoteCount'] == quote_count + 1

    def test_add_multiple_attachments(self, forge_client, config_app):
        config_app(env='test')
        client = forge_client('teacher1')
        count = 4

        def job(i, client):
            data = {
                'attachment':
                (io.BytesIO(f'Testing{i}'.encode('utf-8')), 'goal'),
                'attachmentName': f'test{i}',
            }

            rv = client.post('/problem/1/attachment', data=data)
            assert rv.status_code == 200

        threads = []

        for i in range(count):
            threads.append(threading.Thread(target=job, args=(i, client)))
            threads[i].start()

        for i in range(count):
            threads[i].join()

        for i in range(count):
            rv = client.get(f'/problem/1/attachment/test{i}')
            assert rv.status_code == 200
            assert rv.data == f'Testing{i}'.encode('utf-8')

    @pytest.mark.parametrize('attachment_name, status_code, message', [
        ('att2', 200, 'update'),
        ('att', 404, 'a source'),
        ('non-existed', 404, 'can not find'),
    ])
    def test_update_attachment(self, forge_client, config_app, attachment_name,
                               status_code, message):
        config_app(env='test')
        client = forge_client('teacher1')
        rv = client.get('/attachment')

        data = {
            'attachmentName': attachment_name,
        }

        rv = client.put('/problem/1/attachment', data=data)
        assert rv.status_code == status_code, rv.get_json()
        assert message in rv.get_json()['message']

    @pytest.mark.parametrize(
        'key, value, status_code',
        [
            (None, None, 200),
            ('attachmentName', None, 400),
            ('attachmentName', 'non-exist', 404),
        ],
    )
    def test_delete_attachment(
        self,
        forge_client,
        config_app,
        key,
        value,
        status_code,
    ):
        config_app(env='test')
        client = forge_client('teacher1')
        data = {
            'attachmentName': 'att',
        }
        if key:
            if value is None:
                del data[key]
            else:
                data[key] = value

        rv = client.delete('/problem/1/attachment', data=data)
        assert rv.status_code == status_code

        if status_code == 200:
            rv = client.get('/problem/1/attachment/att')
            assert rv.status_code == 404

    def test_concurrently_delete_attachments(self, forge_client, config_app):
        config_app(env='test')
        client = forge_client('teacher1')
        cnt = 10

        make_name = lambda i: f'test-{i}'
        # create attachments
        p = utils.problem.lazy_add(author=User.get_by_username('teacher1'))
        pid = p.pid
        # copy original attachments
        original_attachments = p.attachments[:]
        for i in range(cnt):
            p.insert_attachment(
                io.BytesIO(b'AAAAA'),
                make_name(i),
            )
        # delete attachments
        def delete_one(i):
            rv = client.delete(
                f'/problem/{pid}/attachment',
                data={'attachmentName': make_name(i)},
            )
            assert rv.status_code == 200

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for i in range(cnt):
                executor.submit(delete_one, i)
        p.reload()
        assert p.attachments == original_attachments

    def test_get_an_attachment(self, forge_client, config_app):
        config_app(env='test')
        client = forge_client('teacher1')

        rv = client.get('/problem/1/attachment/att')
        assert rv.status_code == 200
        assert rv.data == b'att'


class TestComment(BaseTester):
    def test_get_comments(self, forge_client, problem_ids, config_app):
        # Get comments
        config_app(env='test')
        client = forge_client('teacher1')
        rv = client.post('/comment',
                         json={
                             'target': 'problem',
                             'id': 1,
                             'title': 'comment',
                             'content': '',
                             'code': ''
                         })
        json = rv.get_json()
        assert rv.status_code == 200
        id = json['data']['id']

        for j in range(3):
            rv = client.post('/comment',
                             json={
                                 'target': 'comment',
                                 'id': id,
                                 'title': f'r{j}',
                                 'content': '',
                                 'code': '',
                             })
            json = rv.get_json()
            assert rv.status_code == 200

        rv = client.get(f'/comment/{id}')
        json = rv.get_json()
        print(json)
        assert len(json['data']['replies']) == 3
        assert rv.status_code == 200

    def test_get_comment_permission(self, forge_client):
        # Create a teacher and comment
        teacher = utils.user.Factory.teacher()
        course = utils.course.lazy_add(teacher=teacher)
        _id = utils.comment.lazy_add_comment(
            author=teacher.pk,
            problem=utils.problem.lazy_add(course=course),
        ).id
        # Check the teacher's permission
        client = forge_client(teacher.username)
        rv = client.get(f'/comment/{_id}/permission')
        json = rv.get_json()
        assert rv.status_code == 200, json
        assert set(json['data']) == {*'wjdsr'}

    def test_oj_comment_permission(
        self,
        forge_client: Callable[[str, Optional[str]], FlaskClient],
    ):
        # Randomly create a comment
        course = utils.course.lazy_add()
        problem = utils.problem.lazy_add(
            course=course,
            is_oj=True,
        )
        _id = utils.comment.lazy_add_comment(problem=problem).id
        # Create another user under the same course
        u = utils.user.Factory.student()
        course.add_student(u)
        # It should not has any permission for previous comment
        client = forge_client(u.username)
        rv = client.get(f'/comment/{_id}/permission')
        rv_json = rv.get_json()
        assert rv.status_code == 200, rv_json
        assert {*rv_json['data']} == set()
