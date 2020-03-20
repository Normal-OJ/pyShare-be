from mongoengine import *

import mongoengine
import os
from datetime import datetime

__all__ = [*mongoengine.__all__]

MONGO_HOST = os.getenv('MONGO_HOST', 'mongomock://localhost')
connect('normal-oj', host=MONGO_HOST)


class Duration(EmbeddedDocument):
    start = DateTimeField(default=datetime.now())
    end = DateTimeField(default=datetime.max)


class User(Document):
    username = StringField(max_length=16, required=True, primary_key=True)
    user_id = StringField(db_field='userId', max_length=24, required=True)
    user_id2 = StringField(db_field='userId2', max_length=24, default='')
    email = EmailField(required=True, unique=True)
    md5 = StringField(required=True, max_length=32)
    active = BooleanField(default=False)
    # role: 0 -> teacher / 1 -> student
    role = IntField(default=1, choices=[0, 1])
    display_name = StringField(db_field='displayName', max_length=64)
    course = ReferenceField('Course', required=True)
    submissions = ListField(ReferenceField('Submission'))
    last_submit = DateTimeField(default=datetime.min)
    AC_problem_ids = ListField(
        IntField(),
        default=list,
        db_field='ACProblemIds',
    )
    AC_submission = IntField(
        default=0,
        db_field='ACSubmission',
    )
    # number of submissions
    submission = IntField(default=0)
    like = IntField(default=0)


class Course(Document):
    name = StringField(primary_key=True, required=True, max_length=64)
    teacher = ReferenceField('User', required=True)
    students = ListField(ReferenceField('User'), default=True)
    problems = ListField(ReferenceField('Problem'), default=list)


class Comment(EmbeddedDocument):
    markdown = StringField(default='', max_length=100000)
    author = ReferenceField('User', required=True)
    submission = ReferenceField('Submission', default=None)
    depth = IntField(default=0, choice=[0, 1])  # 0 is top post, 1 is reply
    created = DateTimeField(default=datetime.now)
    updated = DateTimeField(default=datetime.now)
    deleted = BooleanField(default=False)
    replies = ListField(
        ReferenceField('Comment'),
        dafault=list,
    )


class Problem(Document):
    meta = {'indexes': [{'fields': ['$title']}]}
    pid = SequenceField(required=True, primary_key=True)
    title = StringField(max_length=64, required=True)
    course = ReferenceField('Course', reuired=True)
    description = StringField(max_length=100000, required=True)
    owner = StringField(max_length=16, required=True)
    tags = ListField(StringField(max_length=16), deafult=list)
    attatchments = ListField(FileField())
    comments = EmbeddedDocumentListField('Comment', default=list)


class SubmissionResult(EmbeddedDocument):
    image = ImageField(required=True)
    stdout = StringField(max_length=10**6, required=True)
    stderr = StringField(max_length=10**6, required=True)


class Submission(Document):
    problem = ReferenceField(Problem, required=True)
    user = ReferenceField(User, required=True)
    code = StringField(max_length=10000, default='')
    timestamp = DateTimeField(default=datetime.now)
    result = EmbeddedDocumentField(SubmissionResult, default=None)
