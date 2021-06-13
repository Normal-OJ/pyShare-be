import pytest
from tests.base_tester import BaseTester
from mongo import *
import io
import mongomock.gridfs

mongomock.gridfs.enable_gridfs_integration()


class TestAttachment(BaseTester):
    @pytest.mark.parametrize(
        'key, value, status_code',
        [
            (None, None, 200),
            ('filename', 'a' * 65, 400),
            ('fileObj', None, 404),
        ],
    )
    def test_create_attachment(
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
            'filename': 'test',
            'description': 'haha',
            'fileObj': (io.BytesIO(b'Win'), 'goal'),
        }
        if key:
            data[key] = value
        rv = client.post('/attachment', data=data)
        assert rv.status_code == status_code
        if status_code == 200:
            assert Attachment(
                rv.get_json()['data']['id']).description == 'haha'

    def test_get_attachments(self, forge_client, config_app):
        config_app(env='test')
        client = forge_client('teacher1')

        rv = client.get('/attachment')
        assert rv.status_code == 200
        assert len(rv.get_json()['data']) == 1
        assert rv.get_json()['data'][0]['filename'] == 'atta1'
        assert rv.get_json()['data'][0]['description'] == 'lol'

    def test_get_an_attachment(self, forge_client, config_app):
        config_app(env='test')
        client = forge_client('teacher1')

        rv = client.get('/attachment')
        id = rv.get_json()['data'][0]['id']

        rv = client.get(f'/attachment/{id}')
        assert rv.status_code == 200
        assert rv.data == b'Hmm.'

    def test_update_attachment(self, forge_client, config_app):
        config_app(env='test')
        client = forge_client('teacher1')
        data = {
            'description': 'haha',
            'fileObj': (io.BytesIO(b'Win'), 'goal'),
        }

        rv = client.get('/attachment')
        id = rv.get_json()['data'][0]['id']

        rv = client.put(f'/attachment/{id}', data=data)
        print(rv.get_json())
        assert rv.status_code == 200
        assert Attachment(id).description == 'haha'

    @pytest.mark.parametrize('key, value, status_code', [
        (None, None, 200),
        ('id', 'a' * 24, 404),
        ('user', 'student1', 403),
    ])
    def test_delete_attachment(self, forge_client, config_app, key, value,
                               status_code):
        config_app(env='test')

        client = forge_client('teacher1')
        rv = client.get('/attachment')
        id = rv.get_json()['data'][0]['id']

        data = {'user': 'teacher1', 'id': id}
        if key:
            data[key] = value
        client = forge_client(data['user'])

        rv = client.delete(f'/attachment/{data["id"]}')
        print(rv.get_json())
        assert rv.status_code == status_code

        if status_code == 200:
            assert not bool(Attachment(data["id"]))
