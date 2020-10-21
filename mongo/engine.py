from os import sendfile
from mongoengine import *
import mongoengine
import os
from datetime import datetime
from .utils import Enum

__all__ = [*mongoengine.__all__]

MONGO_HOST = os.getenv('MONGO_HOST', 'mongomock://localhost')
connect('pyShare', host=MONGO_HOST)


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
    active = BooleanField(default=True)
    # role: 0 -> admin / 1 -> teacher / 2 -> student
    role = IntField(default=2, choices=[0, 1, 2])
    courses = ListField(ReferenceField('Course'), default=[])
    # problems this user created
    problems = ListField(ReferenceField('Problem'), default=[])
    # comments this user wrote
    comments = ListField(ReferenceField('Comment'), default=[])
    # comments this user liked
    likes = ListField(
        ReferenceField('Comment'),
        default=[],
        de_field='likedComments',
    )

    @property
    def info(self):
        return {
            'username': self.username,
            'displayedName': self.display_name,
            'md5': self.md5
        }


class Course(Document):
    name = StringField(primary_key=True, required=True, max_length=64)
    teacher = ReferenceField('User', required=True)
    tags = ListField(StringField(max_length=16), deafult=list)
    students = ListField(ReferenceField('User'), default=[])
    problems = ListField(ReferenceField('Problem'), default=[])
    year = IntField(required=True)
    semester = IntField(required=True)


class Tag(Document):
    value = StringField(primary_key=True, required=True, max_length=16)


class CommentStatus(Enum):
    HIDDEN = 0
    SHOW = 1


class Comment(Document):
    meta = {'indexes': ['floor', 'created', 'updated']}
    title = StringField(required=True, max_length=128)
    floor = IntField(required=True)
    content = StringField(required=True, max_length=100000)
    author = ReferenceField('User', required=True)
    problem = ReferenceField('Problem', default=None)
    submissions = ListField(ReferenceField('Submission', default=[]))
    # 0 is direct comment, 1 is reply of comments
    depth = IntField(default=0, choice=[0, 1])
    # those who like this comment
    liked = ListField(ReferenceField('User'), default=[])
    status = IntField(
        default=CommentStatus.SHOW,
        choices=CommentStatus.choices(),
    )
    passed = BooleanField(default=False)
    created = DateTimeField(default=datetime.now)
    updated = DateTimeField(default=datetime.now)
    replies = ListField(
        ReferenceField('Comment'),
        dafault=[],
    )
    # successed / failed execution counter
    success = IntField(default=0)
    fail = IntField(default=0)
    has_accepted = BooleanField(db_field='hasAccepted', default=False)

    @property
    def is_comment(self):
        return self.depth == 0

    @property
    def show(self):
        return self.status == CommentStatus.SHOW

    @property
    def hidden(self):
        return not self.show

    @property
    def submission(self):
        '''
        the lastest submission
        '''
        return self.submissions[-1] if len(self.submissions) else None


class ProblemStatus(Enum):
    ONLINE = 1
    OFFLINE = 0


class Problem(Document):
    meta = {'indexes': [{'fields': ['$title']}, 'timestamp']}
    pid = SequenceField(required=True, primary_key=True)
    height = IntField(default=0)
    title = StringField(max_length=64, required=True)
    course = ReferenceField('Course', reuired=True)
    description = StringField(max_length=100000, required=True)
    author = ReferenceField('User', requried=True)
    tags = ListField(StringField(max_length=16), deafult=[])
    attachments = ListField(FileField(), default=[])
    comments = ListField(ReferenceField('Comment'), default=[])
    timestamp = DateTimeField(default=datetime.now)
    status = IntField(
        default=ProblemStatus.ONLINE,
        choices=ProblemStatus.choices(),
    )
    default_code = StringField(
        default='',
        max_length=100000,
        db_field='defaultCode',
    )
    # whether a user passed this problem
    passed = MapField(BooleanField(default=False), default={})
    is_template = BooleanField(db_field='isTemplate', default=False)

    @property
    def online(self):
        return self.status == ProblemStatus.ONLINE


class SubmissionStatus(Enum):
    PENDING = 0
    COMPLETE = 1
    OUTPUT_LIMIT_EXCEED = 2


class SubmissionState(Enum):
    PENDING = 0
    ACCEPT = 1
    DENIED = 2


class SubmissionResult(EmbeddedDocument):
    files = ListField(FileField(), default=[])
    stdout = StringField(max_length=10**6, default='')
    stderr = StringField(max_length=10**6, default='')


class Submission(Document):
    problem = ReferenceField(Problem, null=True, required=True)
    comment = ReferenceField(Comment, null=True, required=True)
    user = ReferenceField(User, null=True, required=True)
    code = StringField(max_length=10**6, default='')
    timestamp = DateTimeField(default=datetime.now)
    result = EmbeddedDocumentField(SubmissionResult, default=None)
    status = IntField(
        default=SubmissionStatus.PENDING,
        choices=SubmissionStatus.choices(),
    )
    state = IntField(
        default=SubmissionState.PENDING,
        choices=SubmissionState.choices(),
    )
    # is this submission accepted?
    passed = BooleanField(default=False)


# register delete rule. execute here to resolve `NotRegistered`
# exception caused by two-way reference
# see detailed info at https://github.com/MongoEngine/mongoengine/issues/1707
Course.register_delete_rule(User, 'courses', PULL)
User.register_delete_rule(Course, 'teacher', CASCADE)
User.register_delete_rule(Course, 'students', PULL)
User.register_delete_rule(Comment, 'author', CASCADE)
User.register_delete_rule(Submission, 'user', CASCADE)
User.register_delete_rule(Comment, 'liked', PULL)
Problem.register_delete_rule(Course, 'problems', PULL)
Problem.register_delete_rule(User, 'problems', PULL)
Problem.register_delete_rule(Comment, 'problem', CASCADE)
Problem.register_delete_rule(Submission, 'problem', NULLIFY)
Submission.register_delete_rule(Comment, 'submissions', PULL)
Comment.register_delete_rule(Comment, 'replies', PULL)
Comment.register_delete_rule(Submission, 'comment', CASCADE)
Comment.register_delete_rule(User, 'comments', PULL)
Comment.register_delete_rule(User, 'likes', PULL)
Comment.register_delete_rule(Problem, 'comments', PULL)
