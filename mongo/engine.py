from mongoengine import *
from bson import ObjectId
import mongoengine
import re
import hashlib
from datetime import datetime
from .config import config
from .utils import Enum

__all__ = mongoengine.__all__

MOCK_URL = 'mongomock://localhost'
MONGO_HOST = config['MONGO']['HOST'] if config.TESTING else MOCK_URL
connect(config['MONGO']['DB'], host=MONGO_HOST)


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
    value = StringField(primary_key=True, required=True, max_length=16)


class Comment(Document):
    class Status(Enum):
        HIDDEN = 0
        SHOW = 1

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
    has_accepted = BooleanField(db_field='hasAccepted', default=False)

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
    class Status(Enum):
        ONLINE = 1
        OFFLINE = 0

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
    attachments = ListField(EmbeddedDocumentField(ProblemAttachment),
                            default=[])
    comments = ListField(ReferenceField('Comment'), default=[])
    timestamp = DateTimeField(default=datetime.now)
    status = IntField(
        default=Status.ONLINE,
        choices=Status.choices(),
    )
    default_code = StringField(
        default='',
        max_length=100000,
        db_field='defaultCode',
    )
    is_template = BooleanField(db_field='isTemplate', default=False)
    allow_multiple_comments = BooleanField(db_field='allowMultipleComments',
                                           default=False)
    extra = GenericEmbeddedDocumentField(choices=Type.choices(),
                                         default=Type.NormalProblem())

    @property
    def online(self):
        return self.status == self.Status.ONLINE

    @property
    def is_OJ(self):
        return self.extra._cls == 'OJProblem'


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
