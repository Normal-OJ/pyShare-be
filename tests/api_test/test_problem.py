import pytest
from tests.base_tester import BaseTester
from mongo import *
import io
import mongomock.gridfs
from pycallgraph import PyCallGraph
from pycallgraph.output import GraphvizOutput

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
    def test_get_problem(self, forge_client, problem_ids, config_app):
        # Get problems
        config_app(None, 'Test')
        client = forge_client('teacher1')

        for i in range(2,40):
            rv = client.post('/problem', json={
                'title': f'p{i}',
                'description': '',
                'tags': [],
                'course': 'course_108-1',
                'defaultCode': '',
                'status': 1})
            json = rv.get_json()
            print(json)
            assert rv.status_code == 200

        with PyCallGraph(output=GraphvizOutput()):
            rv = client.get('/problem?offset=0&count=-1')
            json = rv.get_json()
            assert len(json['data']) == 39
            assert rv.status_code == 200
