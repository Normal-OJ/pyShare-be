import pytest
from tests.base_tester import BaseTester
from mongo import *
import mongomock.gridfs

mongomock.gridfs.enable_gridfs_integration()


class TestCourse(BaseTester):
    def test_remove_student_also_remove_his_problem(self, forge_client, config_app):
        config_app(None, 'test')
        client = forge_client('teacher1')
        json = {
            'users': ['student1'],
        }

        rv = client.get('/problem/2')
        assert rv.status_code == 200
        rv = client.patch('/course/course_108-1/student/remove', json=json)
        assert rv.status_code == 200
        rv = client.get('/problem/2')
        assert rv.status_code == 404