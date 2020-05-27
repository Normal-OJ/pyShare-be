from app import setup_app
from mongo import *
from mongo import engine

import os
import pytest
import random
import json
import secrets
from datetime import datetime
from zipfile import ZipFile
from collections import defaultdict
from tests.base_tester import random_string, BaseTester
from tests.api_test.test_homework import CourseData
from tests.api_test.test_problem import get_file

MONGO_MOCK_HOST = 'mongomock://localhost'
DB = 'normal-oj'


@pytest.fixture
def config_app():
    def config_app(config=None, env=None):
        return setup_app(config, env)

    yield config_app
    # clean db
    disconnect()
    conn = connect(DB, host=MONGO_MOCK_HOST)
    conn.drop_database(DB)


@pytest.fixture
def config_client(config_app):
    def config_client(config=None, env=None):
        return config_app(config, env).test_client()

    return config_client


@pytest.fixture
def client(config_client):
    return config_client()


@pytest.fixture
def forge_client(client):
    def cookied(username):
        client.set_cookie('test.test', 'piann', User(username).secret)
        return client

    return cookied


@pytest.fixture
def client_admin(forge_client):
    return forge_client('admin')


@pytest.fixture
def client_teacher(forge_client):
    return forge_client('teacher')


@pytest.fixture
def client_student(forge_client):
    return forge_client('student')


@pytest.fixture
def test_token():
    # Token for user: test
    return User('test').secret


@pytest.fixture
def test2_token():
    # Token for user: test2
    return User('test2').secret


def random_problem_data(username=None, status=-1):
    '''
    generate dummy problem data

    Args:
        username: problem owner's name, if not None, add this problem to his/her course
        status: problem status, if -1, random select from {0, 1}
    '''
    s = random_string()
    return {
        'courses':
        [engine.Course.objects.filter(
            teacher=username)[0].course_name] if username else [],
        'status':
        random.randint(0, 1) if status == -1 else status,
        'type':
        0,
        'description':
        '',
        'tags': ['test'],
        'problemName':
        f'prob {s}',
        'testCaseInfo': {
            'language':
            2,
            'fillInTemplate':
            '',
            'cases': [
                {
                    'caseCount': 1,
                    'caseScore': 100,
                    'memoryLimit': 32768,
                    'timeLimit': 1000,
                },
            ],
        }
    }


@pytest.fixture
def make_course(forge_client):
    def make_course(username, students={}, tas=[]):
        '''
        insert a dummy course data into DB

        Args:
            username -> str: course teacher's user name
            students -> dict[str, str]:
                course students, key is student's username and value is student's nickname
            tas -> list[str]:
                a list contains tas' username
        
        Return:
            generated course data
        '''
        # login with user name
        client = forge_client(username)
        # generate random dummy data
        c_data = CourseData(
            name=random_string(),
            teacher=username,
            students=students,
            tas=tas,
        )
        # add course
        assert add_course(
            c_data.name,
            c_data.teacher,
        ) == True, f'course name: {c_data.name}\nteacher: {c_data.teacher}\n'
        # add students and TA
        rv = client.put(
            f'/course/{c_data.name}',
            json={
                'TAs': c_data.tas,
                'studentNicknames': c_data.students
            },
        )
        assert rv.status_code == 200, rv.get_json()

        client.cookie_jar.clear()
        return c_data

    return make_course


@pytest.fixture()
def problem_ids(forge_client, make_course):
    def problem_ids(username, length, add_to_course=False, status=0):
        '''
        insert dummy problems into db

        Args:
            - username: the problem owner's username
            - length: how many problem you want to create
        Return:
            a list of problem id that you create
        '''
        client = forge_client(username)
        rets = []  # created problem ids
        for _ in range(length):
            rv = client.post(
                '/problem/manage',
                json=random_problem_data(
                    username=username if add_to_course else None,
                    status=status,
                ),
            )
            id = rv.get_json()['data']['problemId']
            client.put(f'/problem/manage/{id}', data=get_file('test_case.zip'))

            assert rv.status_code == 200, rv.get_json()
            rets.append(id)
        # don't leave cookies!
        client.cookie_jar.clear()

        return rets

    return problem_ids


@pytest.fixture
def save_source(tmp_path):
    def save_source(filename, source, lang, ext=None):
        '''
        save user source codes to tmp dir
        currently only support one file.

        Args:
            filename: the source code's filename without extension
            source: source code
            lang: programming language, only accept {0, 1, 2}
            ext: main script extension want to use, if None, decided by lang

        Returns:
            a zip file contains source code
        '''
        if not ext:
            ext = ['.c', '.cpp', '.py'][lang]

        # set path
        name = tmp_path / (filename + ext)
        zip_path = tmp_path / f'{name}.zip'

        if name.exists():
            raise FileExistsError(name)

        with open(name, 'w') as f:
            f.write(source)
        with ZipFile(zip_path, 'w') as f:
            f.write(name, arcname=f'main{ext}')
        return True

    return save_source


@pytest.fixture
def get_source(tmp_path):
    def get_source(filename):
        '''
        get users zipped source by filename

        Args:
            filename: a string denote the source code's filename include extension
        
        Returns:
            the zip file
        '''
        path = tmp_path / f'{filename}.zip'

        if not path.exists():
            raise FileNotFoundError(path)

        return open(path, 'rb')

    return get_source


@pytest.fixture
def submit_once(forge_client, get_source):
    def submit_once(name, pid, filename, lang, client=None):
        _client = forge_client(name) if client is None else client
        now = datetime.utcnow()
        rv, rv_json, rv_data = BaseTester.request(
            _client,
            'post',
            '/submission',
            json={
                'problemId': pid,
                'languageType': lang
            },
        )
        assert rv.status_code == 200, rv_json

        submission_id = rv_data['submissionId']
        token = rv_data['token']

        submission = {
            'submissionId': submission_id,
            'problemId': pid,
            'username': name,
            'lang': lang,
            'timestamp': now
        }

        files = {
            'code': (
                get_source(filename),
                f'main.{["c", "cpp", "py"][lang]}',
            )
        }
        rv, rv_json, rv_data = BaseTester.request(
            _client,
            'put',
            f'/submission/{submission_id}?token={token}',
            data=files,
        )
        assert rv.status_code == 200, rv_json

        if client is None:
            _client.cookie_jar.clear()
        return submission_id

    return submit_once


@pytest.fixture
def submit(submit_once, forge_client):
    def submit(names, pids, count, filename='base.c', lang=0):
        n2p = defaultdict(list)  # name to pid

        for n, p, _ in zip(names, pids, 'x' * count):
            n2p[n].append(p)

        n2s = defaultdict(list)  # name to submission id
        for name, ps in n2p.items():
            client = forge_client(name)
            for p in ps:
                n2s[name].append(
                    submit_once(
                        name=name,
                        pid=p,
                        filename=filename,
                        lang=lang,
                        client=client,
                    ))
            client.cookie_jar.clear()

        return n2s

    return submit