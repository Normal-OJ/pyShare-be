import secrets
from typing import Callable, Optional
from flask.testing import FlaskClient
import pytest
import itertools
from pprint import pprint

from mongo import *
from mongo import engine
from tests.base_tester import BaseTester, random_string

from mongo import Token
from tests import utils

A_NAMES = [
    'teacher',
    'admin',
    'teacher-2',
]
S_NAMES = {
    'student': 'Chika.Fujiwara',
    'student-2': 'Nico.Kurosawa',
}


class TestToken:
    def test_assign(self):
        _id = secrets.token_hex()
        token = Token().assign(_id)
        assert token is not None
        assert Token(token).verify(_id) is True


class SubmissionTester:
    init_submission_count = 8
    submissions = []


@pytest.mark.skip('Legacy')
class TestUserGetSubmission(SubmissionTester):
    @classmethod
    @pytest.fixture(autouse=True)
    def on_create(cls, submit, problem_ids):
        pids = [problem_ids(name, 2, True) for name in A_NAMES]
        pids = itertools.chain(*pids)
        pids = [pid for pid in pids if Problem(pid).obj.problem_status == 0]
        pids = itertools.cycle(pids)
        names = S_NAMES.keys()
        names = itertools.cycle(names)

        cls.submissions = submit(
            names,
            pids,
            cls.init_submission_count,
        )

        assert len([*itertools.chain(*cls.submissions.values())
                    ]) == cls.init_submission_count, cls.submissions

        yield

        cls.submissions = []

    def test_normal_get_submission_list(self, forge_client):
        client = forge_client('student')
        rv, rv_json, rv_data = BaseTester.request(
            client,
            'get',
            f'/submission?offset=0&count={self.init_submission_count}',
        )

        pprint(rv_json)

        assert rv.status_code == 200
        assert 'unicorn' in rv_data
        assert len(rv_data['submissions']) == self.init_submission_count

        excepted_field_names = {
            'submissionId',
            'problemId',
            'user',
            'status',
            'score',
            'runTime',
            'memoryUsage',
            'languageType',
            'timestamp',
        }

        for s in rv_data['submissions']:
            assert len(excepted_field_names - set(s.keys())) == 0

    @pytest.mark.parametrize('offset, count', [
        (0, 1),
        (SubmissionTester.init_submission_count // 2, 1),
    ])
    def test_get_truncated_submission_list(self, forge_client, offset, count):
        client = forge_client('student')
        rv, rv_json, rv_data = BaseTester.request(
            client,
            'get',
            f'/submission/?offset={offset}&count={count}',
        )

        pprint(rv_json)

        assert rv.status_code == 200
        assert len(rv_data['submissions']) == 1

    def test_get_submission_list_with_maximun_offset(self, forge_client):
        client = forge_client('student')
        rv, rv_json, rv_data = BaseTester.request(
            client,
            'get',
            f'/submission/?offset={SubmissionTester.init_submission_count}&count=1',
        )

        print(rv_json)

        assert rv.status_code == 400

    def test_get_all_submission(self, forge_client):
        client = forge_client('student')
        rv, rv_json, rv_data = BaseTester.request(
            client,
            'get',
            '/submission/?offset=0&count=-1',
        )

        pprint(rv_json)

        assert rv.status_code == 200
        # only get online submissions
        assert len(rv_data['submissions']) == self.init_submission_count

        offset = self.init_submission_count // 2
        rv, rv_json, rv_data = BaseTester.request(
            client,
            'get',
            f'/submission/?offset={offset}&count=-1',
        )

        pprint(rv_json)

        assert rv.status_code == 200
        assert len(rv_data['submissions']) == (self.init_submission_count -
                                               offset)

    def test_get_submission_count(self, forge_client):
        client = forge_client('student')
        rv, rv_json, rv_data = BaseTester.request(
            client,
            'get',
            '/submission/count',
        )

        assert rv.status_code == 200, rv_json
        assert rv_data['count'] == self.init_submission_count, rv_data

    def test_get_submission_list_over_db_size(self, forge_client):
        client = forge_client('student')
        rv, rv_json, rv_data = BaseTester.request(
            client,
            'get',
            f'/submission/?offset=0&count={self.init_submission_count ** 2}',
        )

        pprint(rv_json)

        assert rv.status_code == 200
        assert len(rv_data['submissions']) == self.init_submission_count

    def test_get_submission_without_login(self, client):
        for _id in self.submissions.values():
            rv = client.get(f'/submission/{_id}')
            pprint(rv.get_json())
            assert rv.status_code == 403, client.cookie_jar

    def test_normal_user_get_others_submission(self, forge_client):
        '''
        let student get all other's submission
        '''
        ids = []
        for name in (set(S_NAMES) - set(['student'])):
            ids.extend(self.submissions[name])

        client = forge_client('student')
        for _id in ids:
            rv, rv_json, rv_data = BaseTester.request(
                client,
                'get',
                f'/submission/{_id}',
            )
            assert rv.status_code == 200
            assert 'code' not in rv_data, Submission(_id).user.username

    def test_get_self_submission(self, client_student):
        ids = self.submissions['student']
        pprint(ids)

        for _id in ids:
            rv, rv_json, rv_data = BaseTester.request(
                client_student,
                'get',
                f'/submission/{_id}',
            )
            assert rv.status_code == 200
            # user can view self code
            assert 'code' in rv_data

        pprint(rv_data)

        # check for fields
        except_fields = {
            'problemId',
            'languageType',
            'timestamp',
            'status',
            'cases',
            'score',
            'runTime',
            'memoryUsage',
            'code',
        }
        missing_field = except_fields - set(rv_data.keys())
        print(missing_field)
        assert len(missing_field) == 0

    @pytest.mark.parametrize('offset, count', [(None, 1), (0, None),
                                               (None, None)])
    def test_get_submission_list_with_missing_args(self, forge_client, offset,
                                                   count):
        client = forge_client('student')
        rv, rv_json, rv_data = BaseTester.request(
            client,
            'get',
            f'/submission/?offset={offset}&count={count}',
        )
        assert rv.status_code == 400

    @pytest.mark.parametrize('offset, count', [(-1, 2), (2, -2)])
    def test_get_submission_list_with_out_ranged_negative_arg(
        self,
        forge_client,
        offset,
        count,
    ):
        client = forge_client('student')
        rv, rv_json, rv_data = BaseTester.request(
            client,
            'get',
            f'/submission/?offset={offset}&count={count}',
        )
        assert rv.status_code == 400

    @pytest.mark.parametrize(
        'key, except_val',
        [
            ('status', -1),
            ('languageType', 0),
            # TODO: need special test for username field
            # TODO: test for submission id filter
            # TODO: test for problem id filter
        ])
    def test_get_submission_list_by_filter(
        self,
        forge_client,
        key,
        except_val,
    ):
        client = forge_client('student')
        rv, rv_json, rv_data = BaseTester.request(
            client,
            'get',
            f'/submission/?offset=0&count=-1&{key}={except_val}',
        )

        pprint(rv_json)

        assert rv.status_code == 200
        assert len(rv_data['submissions']) != 0
        assert all(map(lambda x: x[key] == except_val,
                       rv_data['submissions'])) == True


@pytest.mark.skip('Legacy')
class TestTeacherGetSubmission(SubmissionTester):
    pids = []

    @classmethod
    @pytest.fixture(autouse=True)
    def on_create(cls, problem_ids, submit):
        # make submissions
        cls.pids = []
        for name in A_NAMES:
            cls.pids.extend(problem_ids(name, 3, True, -1))
        names = itertools.cycle(['admin'])
        submit(
            names,
            itertools.cycle(cls.pids),
            cls.init_submission_count,
        )

    def test_teacher_can_get_offline_submission(self, forge_client):
        client = forge_client('teacher')
        rv, rv_json, rv_data = BaseTester.request(
            client,
            'get',
            '/submission?offset=0&count=-1',
        )

        pprint(rv_json)

        user = User('teacher')
        except_count = len([
            *filter(
                lambda s: can_view(
                    user,
                    s.problem,
                ),
                engine.Submission.objects,
            )
        ])

        assert len(rv_data['submissions']) == except_count

    def test_teacher_can_view_students_source(self, forge_client):
        teacher_name = 'teacher'
        client = forge_client(teacher_name)
        rv, rv_json, rv_data = BaseTester.request(
            client,
            'get',
            '/submission?offset=0&count=-1',
        )

        problems = [Problem(pid).obj for pid in self.pids]
        problems = {p.problem_id for p in problems if p.owner == teacher_name}
        submission_ids = [
            s['submissionId'] for s in rv_data['submissions']
            if s['problemId'] in problems
        ]

        for _id in submission_ids:
            rv, rv_json, rv_data = BaseTester.request(
                client,
                'get',
                f'/submission/{_id}',
            )
            assert 'code' in rv_data, rv_data


class TestCreateSubmission:
    def test_add_in_self_course(
        self,
        forge_client: Callable[[str, Optional[str]], FlaskClient],
    ):
        user = utils.user.Factory.student()
        comment = utils.comment.lazy_add_comment(author=user)
        code = 'print("My super awesome code")'
        client = forge_client(user.username)
        rv = client.post(
            f'/comment/{comment.id}/submission',
            json={'code': code},
        )
        assert rv.status_code == 200
        _id = rv.get_json()['data']['submissionId']
        assert rv.status_code == 200
        assert Submission(_id).code == code

    def test_no_source(
        cls,
        forge_client: Callable[[str, Optional[str]], FlaskClient],
    ):
        user = utils.user.Factory.student()
        comment = utils.comment.lazy_add_comment(author=user)
        client = forge_client(user.username)
        # Send a json but without source code
        rv = client.post(f'/comment/{comment.id}/submission', json={})
        assert rv.status_code == 400

    def test_submit_to_others(
        cls,
        forge_client: Callable[[str, Optional[str]], FlaskClient],
    ):
        user = utils.user.Factory.student()
        comment = utils.comment.lazy_add_comment()
        assert comment.author != user
        client = forge_client(user.username)
        rv = client.post(
            f'/comment/{comment.id}/submission',
            json={'code': 'print("Yabe")'},
        )
        assert rv.status_code == 403
