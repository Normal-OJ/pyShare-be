import pytest
from tests.base_tester import BaseTester
from mongo import *
import io
import mongomock.gridfs

mongomock.gridfs.enable_gridfs_integration()


def get_file(file):
    with open("./tests/problem_test_case/" + file, 'rb') as f:
        return {'case': (io.BytesIO(f.read()), "test_case.zip")}


class ProblemData:
    def __init__(
        self,
        name,
        status=1,
        type=0,
        description='',
        tags=[],
        test_case_info={
            'language':
            1,
            'fillInTemplate':
            '',
            'cases': [{
                'caseCount': 1,
                'caseScore': 100,
                'memoryLimit': 1000,
                'timeLimit': 1000
            }]
        }):
        self.name = name
        self.status = status
        self.type = type
        self.description = description
        self.tags = tags
        self.test_case = get_file(test_case)
        self.test_case_info = test_case_info


# First problem (offline)
@pytest.fixture(params=[{'name': 'Hello World!'}])
def problem_data(request, client_admin):
    BaseTester.setup_class()
    pd = ProblemData(**request.param)
    # add problem
    rv = client_admin.post('/problem/manage',
                           json={
                               'status': pd.status,
                               'type': pd.type,
                               'problemName': pd.name,
                               'description': pd.description,
                               'tags': pd.tags,
                               'testCaseInfo': pd.test_case_info
                           })
    id = rv.get_json()['data']['problemId']
    rv = client_admin.put(f'/problem/manage/{id}',
                          data=get_file('test_case.zip'))
    yield pd
    BaseTester.teardown_class()


# Online problem
@pytest.fixture(params=[{'name': 'Goodbye health~', 'status': 0}])
def another_problem(request, problem_data):
    return problem_data(request)


class TestProblem(BaseTester):
    def test_get_problems(self, forge_client, config_app):
        # Get problems
        config_app(None, 'test')
        client = forge_client('teacher1')

        rv = client.post('/problem',
                         json={
                             'title': 'test',
                             'description': '',
                             'tags': [],
                             'course': 'course_108-1',
                             'defaultCode': '',
                             'status': 1,
                             'isTemplate': False,
                             'allowMultipleComments': True,
                         })
        json = rv.get_json()
        print(json)
        assert rv.status_code == 200

        rv = client.get('/problem?offset=0&count=-1')
        json = rv.get_json()
        assert len(json['data']) == 3
        assert rv.status_code == 200

    def test_get_comments(self, forge_client, problem_ids, config_app):
        # Get comments
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

    @pytest.mark.parametrize('key, value, status_code, message', [
        (None, None, 200, 'your file'),
        (['attachmentName', 'attachment'], ['atta1', None], 200, 'db file'),
        ('attachmentName', None, 400, None),
        ('attachmentName', 'att', 400, None),
        ('attachment', None, 404, None),
    ])
    def test_add_attachment(self, forge_client, config_app, key, value,
                            status_code, message):
        config_app(None, 'test')
        client = forge_client('teacher1')
        data = {
            'attachment': (io.BytesIO(b'Win'), 'goal'),
            'attachmentName': 'haha',
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

        rv = client.post('/problem/1/attachment', data=data)
        assert rv.status_code == status_code

        if message:
            assert message in rv.get_json()['message']

        if status_code == 200:
            rv = client.get(f'/problem/1/attachment/{data["attachmentName"]}')
            assert rv.status_code == 200

    @pytest.mark.parametrize('key, value, status_code', [
        (None, None, 200),
        ('attachmentName', None, 400),
        ('attachmentName', 'non-exist', 404),
    ])
    def test_delete_attachment(self, forge_client, config_app, key, value,
                               status_code):
        config_app(None, 'test')
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

    def test_get_an_attachment(self, forge_client, config_app):
        config_app(None, 'test')
        client = forge_client('teacher1')

        rv = client.get('/problem/1/attachment/att')
        assert rv.status_code == 200
        assert rv.data == b'att'
