from tests.base_tester import BaseTester
from mongo import *


class TestCourse(BaseTester):
    def test_get_course_permission(self, forge_client, config_app):
        config_app(None, 'test')
        client = forge_client('teacher1')

        rv = client.get(f'/course/course_108-1/permission')
        json = rv.get_json()
        assert rv.status_code == 200
        assert set(json['data']) == {*'rwp'}
