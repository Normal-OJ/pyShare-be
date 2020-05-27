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
    def test_get_problems(self, forge_client, problem_ids, config_app):
        # Get problems
        config_app(None, 'Test')
        client = forge_client('teacher1')

        rv = client.post('/problem', json={
            'title': 'test',
            'description': '',
            'tags': [],
            'course': 'course_108-1',
            'defaultCode': '',
            'status': 1})
        json = rv.get_json()
        assert rv.status_code == 200

        rv = client.get('/problem?offset=0&count=-1')
        json = rv.get_json()
        assert len(json['data']) == 2
        assert rv.status_code == 200

    def test_get_commentss(self, forge_client, problem_ids, config_app):
        # Get comments
        config_app(None, 'Test')
        client = forge_client('teacher1')

        rv = client.post('/comment', json={
            'target': 'problem',
            'id': 1,
            'title': 'comment',
            'content': '',
            'code': ''})
        json = rv.get_json()
        assert rv.status_code == 200
        id = json['data']['id']

        for j in range(3):
            rv = client.post('/comment', json={
            'target': 'comment',
            'id': id,
            'title': f'r{j}',
            'content': '',
            'code': '', })
            json = rv.get_json()
            assert rv.status_code == 200

        rv = client.get(f'/comment/{id}')
        json = rv.get_json()
        print(json)
        assert len(json['data']['replies'])==3
        assert rv.status_code == 200
