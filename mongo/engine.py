from mongoengine import *

import mongoengine
import os
from datetime import datetime

__all__ = [*mongoengine.__all__]

MONGO_HOST = os.getenv('MONGO_HOST', 'mongomock://localhost')
connect('normal-oj', host=MONGO_HOST)


class User(Document):
    username = StringField(max_length=16, required=True, primary_key=True)
    display_name = StringField(
        db_field='displayName',
        max_length=32,
        required=True,
    )
    user_id = StringField(db_field='userId', max_length=24, required=True)
    user_id2 = StringField(db_field='userId2', max_length=24, default='')
    email = EmailField(required=True, unique=True)
    md5 = StringField(required=True, max_length=32)
    active = BooleanField(default=False)
    # role: 0 -> admin / 1 -> teacher / 2 -> student
    role = IntField(default=2, choices=[0, 1, 2])
    course = ReferenceField('Course', default=None, null=True)
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
    # the number of like this user receive
    like = IntField(default=0)
    # problems this user created
    problems = ListField(ReferenceField('Problem'), default=[])
    # comments this user wrote
    comments = ListField(ReferenceField('Comment'), default=[])
    # comments this user liked
    liked_comments = ListField(
        ReferenceField('Comment'),
        default=[],
        de_field='likedComments',
    )
    # successed / failed execution counter
    success = IntField(default=0)
    fail = IntField(default=0)


class Course(Document):
    name = StringField(primary_key=True, required=True, max_length=64)
    teacher = ReferenceField('User', required=True)
    students = ListField(ReferenceField('User'), default=[])
    problems = ListField(ReferenceField('Problem'), default=[])


class Comment(Document):
    title = StringField(default='', max_length=128)
    markdown = StringField(default='', max_length=100000)
    author = ReferenceField('User', required=True)
    submission = ReferenceField('Submission', default=None)
    # 0 is top post, 1 is reply
    depth = IntField(default=0, choice=[0, 1])
    # how much user like this comment
    like = IntField(default=0)
    # 0: hidden / 1: show
    status = IntField(default=1)
    created = DateTimeField(default=datetime.now)
    updated = DateTimeField(default=datetime.now)
    replies = ListField(
        ReferenceField('Comment'),
        dafault=[],
    )


class Problem(Document):
    meta = {'indexes': [{'fields': ['$title']}, 'pid']}
    pid = SequenceField(required=True, primary_key=True)
    title = StringField(max_length=64, required=True)
    course = ReferenceField('Course', reuired=True)
    description = StringField(max_length=100000, required=True)
    author = ReferenceField('User', requried=True)
    tags = ListField(StringField(max_length=16), deafult=[])
    attachments = ListField(FileField(), default=[])
    comments = ListField(ReferenceField('Comment'), default=[])
    timestamp = DateTimeField(default=datetime.now)
    # 1: online / 0: offline
    status = IntField(default=1)
    default_code = StringField(
        default='',
        max_length=100000,
        db_field='defaultCode',
    )
    # whether a user passed this problem
    passed = MapField(BooleanField(default=False), default={})


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


# register delete rule. execute here to resolve `NotRegistered`
# exception caused by two-way reference
# see detailed info at https://github.com/MongoEngine/mongoengine/issues/1707
User.register_delete_rule(Problem, 'problems', PULL)
User.register_delete_rule(Comment, 'comments', PULL)
User.register_delete_rule(Comment, 'liked_comments', PULL)
User.register_delete_rule(Course, 'course', NULLIFY)
Course.register_delete_rule(User, 'teacher', NULLIFY)
Course.register_delete_rule(User, 'students', PULL)
Course.register_delete_rule(Problem, 'problems', PULL)
Comment.register_delete_rule(User, 'author', NULLIFY)
Comment.register_delete_rule(Submission, 'submission', NULLIFY)
Comment.register_delete_rule(Comment, 'replies', NULLIFY)
Problem.register_delete_rule(Course, 'course', NULLIFY)
Problem.register_delete_rule(User, 'author', NULLIFY)
Submission.register_delete_rule(Problem, 'problem', NULLIFY)
Submission.register_delete_rule(User, 'user', NULLIFY)