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
            ('tags', 'not-existed', 404),
            ('tags', '', 200),
            ('tags', 'tag2', 200),
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
            'patchNote': 'release',
        }
        if key:
            data[key] = value
        rv = client.post('/attachment', data=data)
        assert rv.status_code == status_code, rv.get_json()
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
        assert rv.get_json()['data'][0]['size'] == 4

    def test_get_an_attachments(self, forge_client, config_app):
        config_app(env='test')
        client = forge_client('teacher1')

        rv = client.get('/attachment')
        id = rv.get_json()['data'][0]['id']

        rv = client.get(f'/attachment/{id}/meta')
        assert rv.status_code == 200
        assert rv.get_json()['data']['filename'] == 'atta1'
        assert rv.get_json()['data']['description'] == 'lol'
        assert rv.get_json()['data']['size'] == 4

    def test_get_attachment_file(self, forge_client, config_app):
        config_app(env='test')
        client = forge_client('teacher1')

        rv = client.get('/attachment')
        id = rv.get_json()['data'][0]['id']

        rv = client.get(f'/attachment/{id}')
        assert rv.status_code == 200
        assert rv.data == b'Hmm.'

        rv = client.get(f'/attachment/{id}/meta')
        assert rv.status_code == 200
        assert rv.get_json()['data']['downloadCount'] == 1

    def test_update_attachment(self, forge_client, config_app):
        config_app(env='test')
        client = forge_client('teacher1')
        rv = client.get('/attachment')
        id = rv.get_json()['data'][0]['id']
        notes = rv.get_json()['data'][0]['patchNotes']

        data = {
            'description': 'haha',
            'fileObj': (io.BytesIO(b'Win'), 'goal'),
            'patchNote': 'update',
            'tags': 'tag1,tag2',
            'filename': 'edited',
        }

        rv = client.put(f'/attachment/{id}', data=data)
        print(rv.get_json())
        assert rv.status_code == 200, rv.get_json()
        assert Attachment(id).description == 'haha'
        assert len(notes) == Attachment(id).version_number - 1

        notif = User.get_by_username('teacher1').notifs[0].info.to_dict()
        assert notif['problem_id'] == 1
        assert notif['name'] == 'att2'

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
