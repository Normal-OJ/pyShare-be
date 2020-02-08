import pytest
from tests.base_tester import BaseTester
from mongo import *
import io


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
