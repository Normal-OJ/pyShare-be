from datetime import timedelta, datetime
from typing import Callable, Optional
import pytest
import mongomock.gridfs
from flask.testing import FlaskClient
from mongo import *
from mongo import requirement
from mongo import engine
from tests.base_tester import BaseTester
from tests import utils

mongomock.gridfs.enable_gridfs_integration()


class TestCourse(BaseTester):
    def test_remove_student_also_remove_his_problem(
        self,
        forge_client,
        config_app,
    ):
        config_app(env='test')
        client = forge_client('teacher1')

        rv = client.get('/problem/2')
        assert rv.status_code == 200
        cid = Course.get_by_name('course_108-1').pk
        users = [str(User.get_by_username('student1').pk)]
        rv = client.patch(
            f'/course/{cid}/student/remove',
            json={
                'users': users,
            },
        )
        assert rv.status_code == 200
        rv = client.get('/problem/2')
        assert rv.status_code == 404

    def test_remove_non_student_is_useless(
        self,
        forge_client,
        config_app,
    ):
        config_app(env='test')
        client = forge_client('admin')
        admin = User.get_by_username('admin')

        id = utils.comment.lazy_add_comment(
            author=admin,
            problem=Problem(1),
        ).id

        rv = client.get(f'/comment/{id}')
        assert rv.status_code == 200

        client = forge_client('teacher1')
        cid = Course.get_by_name('course_108-1').pk
        users = [str(admin.pk)]
        rv = client.patch(
            f'/course/{cid}/student/remove',
            json={
                'users': users,
            },
        )
        assert rv.status_code == 400, rv.get_json()
        rv = client.get(f'/comment/{id}')
        assert rv.status_code == 200

    def test_remove_student_also_remove_his_comment(
        self,
        forge_client,
        config_app,
    ):
        config_app(env='test')
        client = forge_client('student1')
        student = User.get_by_username('student1')

        id = utils.comment.lazy_add_comment(
            author=student,
            problem=Problem(1),
        ).id

        rv = client.get(f'/comment/{id}')
        assert rv.status_code == 200

        client = forge_client('teacher1')
        cid = Course.get_by_name('course_108-1').pk
        users = [str(student.pk)]
        rv = client.patch(
            f'/course/{cid}/student/remove',
            json={
                'users': users,
            },
        )
        assert rv.status_code == 200
        # Access a deleted comment will get 403
        rv = client.get(f'/comment/{id}')
        assert rv.status_code == 403

    def test_remove_student_also_remove_his_like(
        self,
        forge_client,
        config_app,
    ):
        config_app(env='test')
        # Create a comment by teacher
        client = forge_client('teacher1')
        rv = client.post(
            '/comment',
            json={
                'target': 'problem',
                'id': 3,
                'title': 'comment',
                'content': '',
                'code': ''
            },
        )
        assert rv.status_code == 200
        # Student like that comment
        id = rv.get_json()["data"]["id"]
        client = forge_client('student1')
        rv = client.get(f'/comment/{id}/like')
        assert rv.status_code == 200
        rv = client.get(f'/comment/{id}')
        assert len(rv.get_json()['data']['liked']) == 1, rv.get_json()
        # Remove student from course
        client = forge_client('teacher1')
        cid = Course.get_by_name('course_108-1').pk
        users = [str(User.get_by_username('student1').pk)]
        rv = client.patch(
            f'/course/{cid}/student/remove',
            json={
                'users': users,
            },
        )
        assert rv.status_code == 200
        # Check the like has been removed
        client = forge_client('teacher1')
        rv = client.get(f'/comment/{id}')
        assert rv.status_code == 200, rv.get_json()
        assert len(rv.get_json()['data']['liked']) == 0, rv.get_json()

    def test_get_course_permission(
        self,
        forge_client,
        config_app,
    ):
        config_app(env='test')
        client = forge_client('teacher1')

        cid = Course.get_by_name('course_108-1').pk
        rv = client.get(f'/course/{cid}/permission')
        json = rv.get_json()
        assert rv.status_code == 200
        excepted_permission = ( \
            Course.Permission.READ |
            Course.Permission.WRITE |
            Course.Permission.PARTICIPATE
        )
        assert json['data'] == excepted_permission.value

    def test_get_course(
        self,
        forge_client: Callable[[str], FlaskClient],
        config_app,
    ):
        config_app(env='test')
        client = forge_client('teacher1')
        rv = client.get('/course')
        rv_json = rv.get_json()
        assert rv.status_code == 200, rv_json
        course = rv_json['data'][0]
        keys = [
            'id',
            'name',
            'teacher',
            'description',
            'year',
            'semester',
            'status',
        ]
        for key in keys:
            assert key in course


class TestCourseStatistic:
    @classmethod
    def setup_class(cls):
        '''
        Clean DB before each testcase
        '''
        utils.mongo.drop_db()

    def test_empty_course_statistic(
        self,
        forge_client: Callable[[str, Optional[str]], FlaskClient],
    ):
        # Setup course and student
        c = utils.course.lazy_add()
        student = utils.user.lazy_signup(username='student')
        c.add_student(student)
        # Get statistic
        client = forge_client(student.username)
        rv = client.get(f'/course/{c.id}/statistic')
        rv_json = rv.get_json()
        assert rv.status_code == 200, rv_json
        statistic = rv_json['data']
        assert len(statistic) == 1
        keys = {
            'problems',
            'likes',
            'comments',
            'replies',
            'liked',
            'execInfo',
        }
        for key in keys:
            assert statistic[0][key] == []

    @pytest.mark.parametrize('pids', ('', None, 'no-a-number'))
    def test_oj_statistic_missing_pid(
        self,
        forge_client: Callable[[str, Optional[str]], FlaskClient],
        pids: str,
    ):
        # Setup course and student
        c = utils.course.lazy_add()
        student = utils.user.lazy_signup(username='student')
        c.add_student(student)
        # Get statistic
        client = forge_client(student.username)
        rv = client.get(
            f'/course/{c.id}/statistic/oj-problem',
            query_string={'pids': pids},
        )
        rv_json = rv.get_json()
        assert rv.status_code == 400, rv_json
        assert 'pid' in rv_json['message']

    def test_oj_statistic(
        self,
        forge_client: Callable[[str, Optional[str]], FlaskClient],
    ):
        # Setup course and student
        c = utils.course.lazy_add()
        student = utils.user.lazy_signup(username='student')
        c.add_student(student)
        # Create some oj problem
        cnt = 10
        ps = [
            utils.problem.lazy_add(
                course=c,
                author=c.teacher,
                is_oj=True,
            ) for _ in range(cnt)
        ]
        # Get statistic
        client = forge_client(student.username)
        rv = client.get(
            f'/course/{c.id}/statistic/oj-problem',
            query_string={'pids': ','.join(str(p.pid) for p in ps)},
        )
        rv_json = rv.get_json()
        assert rv.status_code == 200, rv_json
        # TODO: validate response data


class TestRecord:
    def setup_method(self):
        ISandbox.use(utils.submission.MockSandbox)

    def teardown_method(self):
        utils.mongo.drop_db()
        ISandbox.use(None)

    def test_get_task_record(
        self,
        forge_client: Callable[[str], FlaskClient],
    ):
        course = utils.course.Factory.readonly()
        problem = utils.problem.lazy_add(course=course)
        task = utils.task.lazy_add(course=course)
        reqs = [
            requirement.LeaveComment.add(
                task=task,
                problem=problem,
                required_number=1,
            )
        ]
        student = utils.course.student(course=course)
        client = forge_client(course.teacher.username)
        rv = client.get(f'/course/{course.id}/task/{task.id}/record')
        assert rv.status_code == 200, rv.get_json()
        record_data = rv.get_json()['data']
        excepted_req = {
            'id':
            str(reqs[0].id),
            'cls':
            'LeaveComment',
            'completes': [
                {
                    'userInfo': {
                        **student.info,
                        'id': str(student.id),
                    },
                    'progress': [0, 1],
                    'completes': None,
                },
            ]
        }
        assert record_data['requirements'][0] == excepted_req

    def test_get_all_task_record(
        self,
        forge_client: Callable[[str], FlaskClient],
    ):
        course = utils.course.Factory.readonly()
        problem = utils.problem.lazy_add(course=course)
        task = utils.task.lazy_add(course=course)
        requirement.LeaveComment.add(
            task=task,
            problem=problem,
            required_number=1,
        )
        student = utils.course.student(course=course)
        client = forge_client(course.teacher.username)
        rv = client.get(f'/course/{course.id}/task/record')
        assert rv.status_code == 200, rv.get_json()
        record_data = rv.get_json()['data']
        assert len(record_data) == 1
        assert record_data[0]['id'] == str(task.id)
        excepted_req = {
            'userInfo': {
                **student.info,
                'id': str(student.id),
            },
            'progress': [0, 1],
            'completes': None,
        }
        assert record_data[0]['completes'][0] == excepted_req

    def test_student_cannot_get_record(
        self,
        forge_client: Callable[[str], FlaskClient],
    ):
        course = utils.course.Factory.readonly()
        task = utils.task.lazy_add(course=course)
        student = utils.course.student(course=course)
        client = forge_client(student.username)
        rv = client.get(f'/course/{course.id}/task/{task.id}/record')
        assert rv.status_code == 403
        rv = client.get(f'/course/{course.id}/task/record')
        assert rv.status_code == 403

    def test_get_task_record_with_extended_due_date(
        self,
        forge_client: Callable[[str], FlaskClient],
    ):
        # Setup task
        now = datetime.now()
        course = utils.course.lazy_add()
        task = utils.task.lazy_add(
            course=course,
            ends_at=now,
        )
        problem = utils.problem.lazy_add(course=course, is_oj=True)
        req = requirement.SolveOJProblem.add(
            task=task,
            problems=[problem],
        )
        # Create a AC submission
        student = utils.course.student(course=course)
        submission = utils.submission.lazy_add_new(
            user=student,
            problem=problem,
        )
        submission.complete(judge_result=submission.engine.JudgeResult.AC)
        assert task.reload().progress(student) == (0, 1)
        # Try get result with extended due
        client = forge_client(course.teacher.username)
        rv = client.get(
            f'/course/{course.id}/task/{task.id}/record',
            query_string={'endsAt': (now + timedelta(days=1)).isoformat()},
        )
        assert rv.status_code == 200, rv.get_json()
        record_data = rv.get_json()['data']
        req_records = record_data['requirements']
        assert req_records[0]['id'] == str(req.id)
        student_completes = req_records[0]['completes'][0]
        assert student_completes['userInfo'] == {
            **student.info,
            'id': str(student.id),
        }
        assert student_completes['progress'] == [1, 1]
