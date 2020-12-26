import pytest
from tests.base_tester import BaseTester
from mongo import *
import io
import mongomock.gridfs

mongomock.gridfs.enable_gridfs_integration()


class TestAttachment(BaseTester):
    @pytest.mark.parametrize('key, value, status_code', [
        (None, None, 200),
        ('filename', 'atta1', 400),
        ('filename', 'a' * 65, 400),
        ('fileObj', None, 404),
    ])
    def test_create_attachment(self, forge_client, config_app, key, value,
                               status_code):
        config_app(None, 'test')
        client = forge_client('teacher1')
        data = {
            'filename': 'test',
            'description': 'haha',
            'fileObj': (io.BytesIO(b'Win'), 'goal'),
        }
        if key:
            data[key] = value

        rv = client.post('/attachment', data=data)
        assert rv.status_code == status_code

    def test_get_attachments(self, forge_client, config_app):
        config_app(None, 'test')
        client = forge_client('teacher1')

        rv = client.get('/attachment')
        assert rv.status_code == 200
        assert rv.get_json()['data'] == [{
            'filename': 'atta1',
            'description': 'lol',
        }]

    def test_get_an_attachment(self, forge_client, config_app):
        config_app(None, 'test')
        client = forge_client('teacher1')

        rv = client.get('/attachment/atta1')
        assert rv.status_code == 200
        assert rv.data == b'Hmm.'

    def test_update_attachment(self, forge_client, config_app):
        config_app(None, 'test')
        client = forge_client('teacher1')
        data = {
            'description': 'haha',
            'fileObj': (io.BytesIO(b'Win'), 'goal'),
        }

        rv = client.put('/attachment/atta1', data=data)
        assert rv.status_code == 200

    @pytest.mark.parametrize('key, value, status_code', [
        (None, None, 200),
        ('filename', 'test', 404),
        ('user', 'student1', 403),
    ])
    def test_delete_attachment(self, forge_client, config_app, key, value,
                               status_code):
        config_app(None, 'test')
        data = {'user': 'teacher1', 'filename': 'atta1'}
        if key:
            data[key] = value
        client = forge_client(data['user'])

        rv = client.delete(f'/attachment/{data["filename"]}')
        assert rv.status_code == status_code
