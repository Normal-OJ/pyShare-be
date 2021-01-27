import pytest
from tests.base_tester import BaseTester
from mongo import *
import mongomock.gridfs

mongomock.gridfs.enable_gridfs_integration()


class TestCourse(BaseTester):
    def test_remove_student_also_remove_his_problem(self, forge_client,
                                                    config_app):
        config_app(None, 'test')
        client = forge_client('teacher1')

        rv = client.get('/problem/2')
        assert rv.status_code == 200
        rv = client.patch('/course/course_108-1/student/remove',
                          json={
                              'users': ['student1'],
                          })
        assert rv.status_code == 200
        rv = client.get('/problem/2')
        assert rv.status_code == 404

    def test_remove_student_also_remove_his_comment(self, forge_client,
                                                    config_app):
        config_app(None, 'test')
        client = forge_client('student1')

        rv = client.post('/comment',
                         json={
                             'target': 'problem',
                             'id': 1,
                             'title': 'comment',
                             'content': '',
                             'code': ''
                         })
        assert rv.status_code == 200
        id = rv.get_json()["data"]["id"]
        rv = client.get(f'/comment/{id}')
        assert rv.status_code == 200

        client = forge_client('teacher1')
        rv = client.patch('/course/course_108-1/student/remove',
                          json={
                              'users': ['student1'],
                          })
        assert rv.status_code == 200
        rv = client.get(f'/comment/{id}')
        assert rv.status_code == 404

    def test_remove_student_also_remove_his_like(self, forge_client,
                                                 config_app):
        config_app(None, 'test')
        client = forge_client('teacher1')

        rv = client.post('/comment',
                         json={
                             'target': 'problem',
                             'id': 1,
                             'title': 'comment',
                             'content': '',
                             'code': ''
                         })
        assert rv.status_code == 200
        id = rv.get_json()["data"]["id"]

        client = forge_client('student1')
        rv = client.get(f'/comment/{id}/like')
        assert rv.status_code == 200
        rv = client.get(f'/comment/{id}')
        assert len(rv.get_json()['data']['liked']) == 1

        client = forge_client('teacher1')
        rv = client.patch('/course/course_108-1/student/remove',
                          json={
                              'users': ['student1'],
                          })
        assert rv.status_code == 200

        client = forge_client('student1')
        rv = client.get(f'/comment/{id}')
        assert len(rv.get_json()['data']['liked']) == 0
