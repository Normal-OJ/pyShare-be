from mongoengine import *
from bson import ObjectId
import mongoengine
import os
import re
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
    email = EmailField(max_length=320, required=True, unique=True)
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
    # notification list
    notifs = ListField(ReferenceField('Notif'), default=[])

    @property
    def info(self):
        return {
            'username': self.username,
            'displayName': self.display_name,
            'md5': self.md5
        }


class CourseStatus(Enum):
    PRIVATE = 0
    READONLY = 1
    PUBLIC = 2


class Course(Document):
    class Status(Enum):
        PRIVATE = 0
        READONLY = 1
        PUBLIC = 2

    # course's name can only contain letters, numbers, underscore (_),
    # dash (-) and dot (.), also, it can not be empty
    name = StringField(
        regex=r'^[\w\.\ _\-]+$',
        required=True,
        max_length=64,
    )
    teacher = ReferenceField('User', required=True)
    tags = ListField(StringField(max_length=16), default=list)
    students = ListField(ReferenceField('User'), default=[])
    problems = ListField(ReferenceField('Problem'), default=[])
    year = IntField(required=True)
    semester = IntField(required=True)
    description = StringField(default='', max_length=10**4)
    status = IntField(
        default=CourseStatus.PUBLIC,
        choices=CourseStatus.choices(),
    )


class Tag(Document):
    value = StringField(primary_key=True, required=True, max_length=16)


class CommentStatus(Enum):
    HIDDEN = 0
    SHOW = 1


class Comment(Document):
    meta = {'indexes': ['floor', 'created', 'updated']}
    title = StringField(required=True, max_length=128)
    floor = IntField(required=True)
    content = StringField(required=True, max_length=5000000)
    author = ReferenceField('User', required=True)
    problem = ReferenceField('Problem', required=True)
    submissions = ListField(ReferenceField('Submission', default=[]))
    # 0 is direct comment, 1 is reply of comments
    depth = IntField(default=0, choice=[0, 1])
    # those who like this comment
    liked = ListField(ReferenceField('User'), default=[])
    status = IntField(
        default=CommentStatus.SHOW,
        choices=CommentStatus.choices(),
    )
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


class Attachment(Document):
    filename = StringField(max_length=64, required=True, primary_key=True)
    description = StringField(max_length=5000000, required=True)
    file = FileField(required=True)


class ProblemStatus(Enum):
    ONLINE = 1
    OFFLINE = 0


class Problem(Document):
    meta = {'indexes': [{'fields': ['$title']}, 'timestamp']}
    pid = SequenceField(required=True, primary_key=True)
    height = IntField(default=0)
    title = StringField(max_length=64, required=True)
    course = ReferenceField('Course', reuired=True)
    description = StringField(max_length=5000000, required=True)
    author = ReferenceField('User', requried=True)
    tags = ListField(StringField(max_length=16), default=[])
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
    is_template = BooleanField(db_field='isTemplate', default=False)
    allow_multiple_comments = BooleanField(db_field='allowMultipleComments',
                                           default=False)

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
    comment = ReferenceField(Comment, null=True)
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


class Notif(Document):
    class Type(Enum):
        class __Base__(EmbeddedDocument):
            DICT_FEILDS = {'type': 'type_name'}
            meta = {'allow_inheritance': True}

            @property
            def type_name(self) -> str:
                # This regular expression finds the zero-length position
                # whose next character is an uppercase letter.
                return re.compile(r'(?<!^)(?=[A-Z])').sub(
                    '_', self.__class__.__name__).upper()

            def to_dict(self) -> dict:
                def resolve(attrs):
                    ret = self
                    for attr in attrs:
                        ret = ret.__getattribute__(attr)
                    if isinstance(ret, ObjectId):
                        ret = str(ret)
                    return ret

                return {
                    k: resolve(self.DICT_FEILDS[k].split('.'))
                    for k in self.DICT_FEILDS
                }

        class Grade(__Base__):
            DICT_FEILDS = {
                'type': 'type_name',
                'comment_id': 'comment.id',
                'result': 'result',
                'problem_id': 'problem.id',
            }

            comment = ReferenceField(Comment)
            result = IntField(required=True, choices=SubmissionState.choices())
            problem = ReferenceField(Problem)

        class Like(__Base__):
            DICT_FEILDS = {
                'type': 'type_name',
                'comment_id': 'comment.id',
                'liked': 'liked.username',
                'problem_id': 'problem.id',
            }

            comment = ReferenceField(Comment)
            liked = ReferenceField(User)
            problem = ReferenceField(Problem)

        class NewReply(__Base__):
            DICT_FEILDS = {
                'type': 'type_name',
                'comment_id': 'comment.id',
                'problem_id': 'problem.id',
            }

            comment = ReferenceField(Comment)
            problem = ReferenceField(Problem)

        class NewComment(__Base__):
            DICT_FEILDS = {
                'type': 'type_name',
                'problem_id': 'problem.id',
            }

            problem = ReferenceField(Problem)

    class Status(Enum):
        UNREAD = 0
        READ = 1
        HIDDEN = 2

    status = IntField(
        default=Status.UNREAD,
        choices=Status.choices(),
    )
    info = GenericEmbeddedDocumentField(choices=Type.choices())


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
