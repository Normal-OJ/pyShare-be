import pytest

from tests.base_tester import BaseTester, random_string
from datetime import datetime, timedelta, time

from mongo import *


class CourseData:
    def __init__(self, name, teacher, students, tas):
        self.name = name
        self.teacher = teacher
        self.students = students
        self.tas = tas
        self.homework_ids = []

    @property
    def homework_name(self):
        return f'Test HW 4 {self.name} {id(self)}'


@pytest.fixture(params=[{
    'name': 'Programming_I',
    'teacher': 'Po-Wen-Chi',
    'students': {
        'Yin-Da-Chen': 'ala',
        'Bo-Chieh-Chuang': 'bogay'
    },
    'tas': ['Tzu-Wei-Yu']
}])
def course_data(request, client_admin, problem_ids):
    BaseTester.setup_class()

    cd = CourseData(**request.param)
    # add course
    add_course(cd.name, cd.teacher)
    # add students and TA
    client_admin.put(f'/course/{cd.name}',
                     json={
                         'TAs': cd.tas,
                         'studentNicknames': cd.students
                     })
    # add homework
    hw = Homework.add_hw(
        user=User(cd.teacher).obj,
        course_name=cd.name,
        markdown=f'# {cd.homework_name}',
        hw_name=cd.homework_name,
        start=int(datetime.now().timestamp()),
        end=int(datetime.now().timestamp()),
        problem_ids=problem_ids(cd.teacher, 3),
        scoreboard_status=0,
    )
    # append hw id
    cd.homework_ids.append(str(hw.id))

    yield cd

    BaseTester.teardown_class()


@pytest.fixture(
    params={
        'name': 'Advanced_Programming',
        'teacher': 'Tsung-Che-Chiang',
        'students': {
            'Tzu-Wei-Yu': 'Uier',
            'Bo-Chieh-Chuang': 'bogay'
        },
        'tas': ['Yin-Da-Chen']
    })
def another_course(request, course_data, client_admin):
    return course_data(request, client_admin)
