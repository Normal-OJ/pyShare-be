from __future__ import annotations
from typing import List, Optional, Tuple
from mongoengine import *
import mongoengine
import re
import hashlib
from datetime import datetime
from .config import config
from .utils import Enum, logger

__all__ = mongoengine.__all__


# The under score is to prevent conflicting mongoengine.connect
def _connect():
    MOCK_URL = 'mongomock://localhost'
    MONGO_HOST = MOCK_URL if config.TESTING else config['MONGO']['HOST']
    conn = connect(config['MONGO']['DB'], host=MONGO_HOST)
    logger().debug(f'Connect to {MONGO_HOST}')
    return conn


_connect()


class User(Document):
    class Role(Enum):
        ADMIN = 0
        TEACHER = 1
        STUDENT = 2

    username = StringField(
        max_length=16,
        required=True,
    )
    # empty string means "no school"
    school = StringField(
        max_length=16,
        unique_with='username',
        default='',
    )
    display_name = StringField(
        db_field='displayName',
        max_length=32,
        required=True,
    )
    user_id = StringField(db_field='userId', max_length=24, required=True)
    user_id2 = StringField(db_field='userId2', max_length=24, default='')
    email = EmailField(max_length=320)
    md5 = StringField(required=True, max_length=32)
    active = BooleanField(default=True)
    role = IntField(
        default=Role.STUDENT,
        choices=Role.choices(),
    )
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

    @classmethod
    def email_hash(cls, email: str):
        return hashlib.md5(email.encode()).hexdigest()

    @classmethod
    def check_email(cls, email):
        # TODO: solve race condition
        if email is not None and User.objects(email=email):
            cls.email.validate(email)
            raise NotUniqueError('Duplicated not-null email field')

    def update(self, **ks):
        if 'email' in ks:
            self.check_email(ks['email'])
            ks['md5'] = self.email_hash((ks['email'] or ''))
        super().update(**ks)

    def save(self, *args, **ks):
        self.check_email(self.email)
        self.md5 = self.email_hash((self.email or ''))
        super().save(*args, **ks)
        return self.reload()

    @property
    def info(self):
        return {
            'username': self.username,
            'displayName': self.display_name,
            'school': self.school,
            'role': self.role,
            'email': self.email,
            'md5': self.md5,
            'id': self.id,
        }


class Course(Document):
    class Status(Enum):
        PRIVATE = 0
        READONLY = 1
        PUBLIC = 2

    # course's name can only contain letters, numbers, underscore (_),
    # dash (-), dot (.) and space ( ),
    # it can not be empty or begin/end with any space.
    name = StringField(
        regex=r'^[\w\._\-][\w\._\- ]+[\w\._\-]$',
        required=True,
        max_length=64,
    )
    teacher = ReferenceField('User', required=True)
    tags = ListField(StringField(max_length=16), default=list)
    normal_problem_tags = ListField(StringField(max_length=16), default=list)
    OJ_problem_tags = ListField(StringField(max_length=16), default=list)
    students = ListField(ReferenceField('User'), default=[])
    problems = ListField(ReferenceField('Problem'), default=[])
    year = IntField(required=True)
    semester = IntField(required=True)
    description = StringField(default='', max_length=10**4)
    status = IntField(
        default=Status.PUBLIC,
        choices=Status.choices(),
    )


class Tag(Document):
    class Category(Enum):
        COURSE = 0
        ATTACHMENT = 1
        NORMAL_PROBLEM = 2
        OJ_PROBLEM = 3

    value = StringField(primary_key=True, required=True, max_length=16)
    categories = ListField(IntField(choices=Category.choices()), default=[])


class Comment(Document):
    class Status(Enum):
        HIDDEN = 0
        SHOW = 1

    class Acceptance(Enum):
        ACCEPTED = 0
        REJECTED = 1
        PENDING = 2
        NOT_TRY = 3

    meta = {'indexes': ['floor', 'created', 'updated']}
    title = StringField(required=True, max_length=128)
    floor = IntField(required=True)
    content = StringField(required=True, max_length=5000000)
    author = ReferenceField('User', required=True)
    problem = ReferenceField('Problem', required=True)
    submissions = ListField(ReferenceField('Submission'), default=[])
    # 0 is direct comment, 1 is reply of comments
    depth = IntField(default=0, choice=[0, 1])
    # those who like this comment
    liked = ListField(ReferenceField('User'), default=[])
    status = IntField(
        default=Status.SHOW,
        choices=Status.choices(),
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
    acceptance = IntField(
        default=Acceptance.NOT_TRY,
        choices=Acceptance.choices(),
    )

    @property
    def is_comment(self):
        return self.depth == 0

    @property
    def show(self):
        return self.status == self.Status.SHOW

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
    filename = StringField(max_length=64, required=True)
    description = StringField(max_length=5000000, required=True)
    file = FileField(required=True)
    author = ReferenceField('User', requried=True)
    created = DateTimeField(default=datetime.now)
    updated = DateTimeField(default=datetime.now)
    size = IntField(default=0)
    patch_notes = ListField(StringField(max_length=5000000),
                            default=[],
                            db_field='patchNotes')
    tags = ListField(StringField(max_length=16), default=list)
    quote_count = IntField(default=0, db_field='quoteCount')
    download_count = IntField(default=0, db_field='downloadCount')

    @property
    def version_number(self):
        return len(self.patch_notes)

    def to_dict(self):
        return {
            'filename': self.filename,
            'description': self.description,
            'author': self.author.info,
            'created': self.created.timestamp(),
            'updated': self.updated.timestamp(),
            'id': self.id,
            'size': self.size,
            'patchNotes': self.patch_notes,
            'tags': self.tags,
            'downloadCount': self.download_count,
            'quoteCount': self.quote_count
        }


class Problem(Document):
    class Type(Enum):
        class OJProblem(EmbeddedDocument):
            input = StringField(max_length=5000000, required=True)
            output = StringField(max_length=5000000, required=True)

        class NormalProblem(EmbeddedDocument):
            pass

    class ProblemAttachment(EmbeddedDocument):
        file = FileField(required=True)
        source = ReferenceField('Attachment', default=None)
        version_number = IntField(db_field='versionNumber', default=-1)

        @property
        def filename(self):
            return self.file.filename

        @property
        def delete(self):
            return self.file.delete

    meta = {'indexes': [{'fields': ['$title']}, 'timestamp']}
    pid = SequenceField(required=True, primary_key=True)
    height = IntField(default=0)
    title = StringField(max_length=64, required=True)
    course = ReferenceField('Course', reuired=True)
    description = StringField(max_length=5000000, required=True)
    author = ReferenceField('User', requried=True)
    tags = ListField(StringField(max_length=16), default=[])
    attachments = ListField(
        EmbeddedDocumentField(ProblemAttachment),
        default=[],
    )
    comments = ListField(ReferenceField('Comment'), default=[])
    timestamp = DateTimeField(default=datetime.now)
    hidden = BooleanField(default=False)
    default_code = StringField(
        default='',
        max_length=100000,
        db_field='defaultCode',
    )
    is_template = BooleanField(db_field='isTemplate', default=False)
    allow_multiple_comments = BooleanField(
        db_field='allowMultipleComments',
        default=False,
    )
    extra = GenericEmbeddedDocumentField(
        choices=Type.choices(),
        default=Type.NormalProblem(),
    )
    reference_count = IntField(default=0)

    @property
    def online(self):
        return not self.hidden

    @property
    def is_OJ(self):
        return self.extra._cls == 'OJProblem'

    @property
    def tag_category(self):
        return Tag.Category.OJ_PROBLEM if self.is_OJ else Tag.Category.NORMAL_PROBLEM


class Submission(Document):
    meta = {'allow_inheritance': True}

    # TODO: Use more meaningful names for status, state and result

    class Result(EmbeddedDocument):
        files = ListField(FileField(), default=[])
        stdout = StringField(max_length=10**6, default='')
        stderr = StringField(max_length=10**6, default='')
        judge_result = IntField(default=None)

    class JudgeResult(Enum):
        AC = 0
        WA = 1
        OLE = 3

    class Status(Enum):
        PENDING = 0
        COMPLETE = 1
        OUTPUT_LIMIT_EXCEED = 2

    class State(Enum):
        PENDING = 0
        ACCEPT = 1
        DENIED = 2

    problem = ReferenceField(Problem, null=True, required=True)
    comment = ReferenceField(Comment, null=True)
    user = ReferenceField(User, null=True, required=True)
    code = StringField(max_length=10**6, default='')
    timestamp = DateTimeField(default=datetime.now)
    result = EmbeddedDocumentField(Result, default=None)
    status = IntField(
        default=Status.PENDING,
        choices=Status.choices(),
    )
    state = IntField(
        default=State.PENDING,
        choices=State.choices(),
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
                def resolve(attrs: List[str]):
                    ret = self
                    for attr in attrs:
                        ret = ret.__getattribute__(attr)
                    return ret

                return {
                    k: resolve(v.split('.'))
                    for k, v in self.DICT_FEILDS.items()
                }

        class Grade(__Base__):
            DICT_FEILDS = {
                'type': 'type_name',
                'comment_id': 'comment.id',
                'result': 'result',
                'problem_id': 'problem.id',
            }

            comment = ReferenceField(Comment)
            result = IntField(
                required=True,
                choices=Submission.State.choices(),
            )
            problem = ReferenceField(Problem)

        class Like(__Base__):
            DICT_FEILDS = {
                'type': 'type_name',
                'comment_id': 'comment.id',
                'liked': 'liked.info',
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

        class AttachmentUpdate(__Base__):
            DICT_FEILDS = {
                'type': 'type_name',
                'attachment_id': 'attachment.id',
                'problem_id': 'problem.id',
                'name': 'name'
            }

            attachment = ReferenceField(Attachment)
            problem = ReferenceField(Problem)
            name = StringField(max_length=64)

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


class School(Document):
    # Abbreviation of school name
    abbr = StringField(
        max_length=16,
        required=True,
        primary_key=True,
    )
    # School's full name
    name = StringField(max_length=256)

    def to_dict(self):
        return {
            'abbr': self.abbr,
            'name': self.name,
        }


class Sandbox(Document):
    # TODO: URL validation
    url = StringField(requried=True, unique=True)
    token = StringField(required=True)
    alias = StringField(max_length=32)

    def to_json(self):
        ret = {'url': self.url}
        if self.alias:
            ret['alias'] = self.alias
        return ret


class AppConfig(DynamicDocument):
    key = StringField(primary_key=True)


# TODO: Move requirements to individual package


class Requirement(Document):
    meta = {'allow_inheritance': True}
    task = ReferenceField('Task', required=True)

    def completed_at(self, user) -> Optional[datetime]:
        '''
        To query when a user completed this requirement, return None
        if s/he haven't
        '''
        raise NotImplementedError

    def is_completed(self, user):
        return self.completed_at(user) is not None

    def progress(self, user) -> Tuple[int, int]:
        '''
        To query the user progress for this requirement.
        Return a tuple (p, q) which means his/her progress is p/q.
        '''
        raise NotImplementedError


class SolveOJProblem(Requirement):
    class Record(EmbeddedDocument):
        completes = ListField(ReferenceField('Problem'))
        completed_at = DateTimeField()

    problems = ListField(ReferenceField('Problem'))
    records = MapField(EmbeddedDocumentField(Record))

    def get_record(self, user) -> Optional[Record]:
        return self.records.get(str(user.id), self.Record())

    def set_record(self, user, record: Record):
        self.update(**{f'records__{user.id}': record})

    def completed_at(self, user) -> Optional[datetime]:
        record = self.get_record(user)
        if record is None:
            return None
        return record.completed_at

    def progress(self, user) -> Tuple[int, int]:
        return len(self.get_record(user).completes), len(self.problems)


class LeaveComment(Requirement):
    class Record(EmbeddedDocument):
        comments = ListField(ReferenceField('Comment'))
        completed_at = DateTimeField()

    problem = ReferenceField('Problem')
    required_number = IntField(min_value=1, default=1)
    # TODO: Use `EnumField`
    acceptance = IntField(min_value=0, max_value=3)
    records = MapField(EmbeddedDocumentField(Record))

    def get_record(self, user) -> Optional[Record]:
        return self.records.get(str(user.id), self.Record())

    def set_record(self, user, record: Record):
        self.update(**{f'records__{user.id}': record})

    def completed_at(self, user) -> Optional[datetime]:
        record = self.get_record(user)
        if record is None:
            return None
        return record.completed_at

    def progress(self, user) -> Tuple[int, int]:
        return len(self.get_record(user).comments), self.required_number


class ReplyToComment(Requirement):
    class Record(EmbeddedDocument):
        replies = ListField(ReferenceField('Comment'))
        completed_at = DateTimeField()

    required_number = IntField(min_value=1, default=1)
    records = MapField(EmbeddedDocumentField(Record))

    def get_record(self, user) -> Optional[Record]:
        return self.records.get(str(user.id), self.Record())

    def set_record(self, user, record: Record):
        self.update(**{f'records__{user.id}': record})

    def completed_at(self, user) -> Optional[datetime]:
        record = self.get_record(user)
        if record is None:
            return None
        return record.completed_at

    def progress(self, user) -> Tuple[int, int]:
        return len(self.get_record(user).replies), self.required_number


class LikeOthersComment(Requirement):
    class Record(EmbeddedDocument):
        comments = ListField(ReferenceField('Comment'))
        completed_at = DateTimeField()

    required_number = IntField(min_value=1, required=True)
    records = MapField(EmbeddedDocumentField(Record))

    def get_record(self, user) -> Optional[Record]:
        return self.records.get(str(user.id), self.Record())

    def set_record(self, user, record: Record):
        self.update(**{f'records__{user.id}': record})

    def completed_at(self, user) -> Optional[datetime]:
        record = self.get_record(user)
        if record is None:
            return None
        return record.completed_at

    def progress(self, user) -> Tuple[int, int]:
        return len(self.get_record(user).comments), self.required_number


class Task(Document):
    title = StringField(max_length=64, required=True)
    content = StringField(max_length=10000)
    course = ReferenceField('Course', required=True)
    starts_at = DateTimeField(default=datetime.now)
    ends_at = DateTimeField(default=datetime(2111, 10, 10))
    requirements = ListField(
        ReferenceField('Requirement', required=True),
        default=list,
    )

    @queryset_manager
    def active_objects(cls, queryset):
        now = datetime.now()
        return queryset.filter(starts_at__lte=now, ends_at__gte=now)

    def completed_at(self, user) -> Optional[datetime]:
        completed_dates = [
            *filter(
                lambda d: d is not None,
                (req.completed_at(user) for req in self.requirements),
            )
        ]
        if len(completed_dates) == 0:
            return None
        return max(completed_dates)

    def is_completed(self, user) -> bool:
        return self.completed_at(user) is not None

    def progress(self, user) -> Tuple[int, int]:
        p = sum((req.is_completed(user) for req in self.requirements))
        q = len(self.requirements)
        return p, q


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
Requirement.register_delete_rule(Task, 'requirements', PULL)
Task.register_delete_rule(Requirement, 'task', CASCADE)
