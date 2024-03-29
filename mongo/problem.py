from typing import List, Optional, Union
from functools import reduce
import enum
from mongoengine.queryset.visitor import Q
from . import engine
from .engine import GridFSProxy
from .base import MongoBase
from .course import Course
from .user import User
from .utils import doc_required, get_redis_client
from zipfile import ZipFile
import tempfile
import io

__all__ = ['Problem', 'TagNotFoundError']


class TagNotFoundError(Exception):
    pass


class Problem(MongoBase, engine=engine.Problem):
    class Permission(enum.Flag):
        READ = enum.auto()
        WRITE = enum.auto()
        DELETE = enum.auto()
        MANAGE = READ | WRITE | DELETE
        CLONE = enum.auto()
        SUBMIT = enum.auto()
        REJUDGE = enum.auto()

    @doc_required('user', User)
    def own_permission(self, user: User) -> 'Problem.Permission':
        _permission = self.Permission(0)
        if self.online:
            if Course(self.course).permission(
                    user=user,
                    req=Course.Permission.READ,
            ):
                _permission |= self.Permission.READ
        elif user == self.course.teacher:
            _permission |= self.Permission.READ
        # all templates can be used
        if self.is_template:
            _permission |= self.Permission.READ
        # problem author and admin can edit, delete problem
        if user == self.author or user >= 'admin':
            # TODO: admin should not has permission to edit others' problem
            _permission |= self.Permission.MANAGE
        # teachers and above can clone
        if user >= 'teacher':
            _permission |= self.Permission.CLONE
        # people who can write the course can rejudge problem
        if Course(self.course).permission(
                user=user,
                req=Course.Permission.WRITE,
        ):
            _permission |= self.Permission.REJUDGE
        if _permission & self.Permission.READ and Course(
                self.course).permission(
                    user=user,
                    req=Course.Permission.PARTICIPATE,
                ):
            _permission |= self.Permission.SUBMIT
        return _permission

    @doc_required('user', User)
    def permission(self, user: User, req: Permission) -> bool:
        '''
        check user's permission, `req` is the required permission

        Returns:
            a `bool` value denotes whether user has these
            permissions
        '''
        _permission = self.own_permission(user=user)
        return bool(req & _permission)

    @doc_required('target_course', 'target_course', Course)
    @doc_required('user', 'user', User)
    def copy(
        self,
        target_course: Course,
        is_template: bool,
        user: User,
    ):
        '''
        copy the problem to another course, and drop all comments & replies
        '''
        p = self.to_mongo()
        # delete non-shared datas
        for field in (
                'comments',
                'attachments',
                'height',
                '_id',
                'isTemplate',
                'author',
                'course',
        ):
            del p[field]
        # field name conversion
        p['default_code'] = p.pop('defaultCode')
        p['allow_multiple_comments'] = p.pop('allowMultipleComments')
        category = self.tag_category
        new_tags = [
            *({*p['tags']} - {*target_course.get_tags_by_category(category)})
        ]
        target_course.push_tags(new_tags, category)
        try:
            p = Problem.add(
                **p,
                author=user,
                course=target_course,
                is_template=is_template,
            )
            # update attachments
            with get_redis_client().lock(f'{p}-att'):
                p.attachments = [*map(self.copy_attachment, self.attachments)]
                p.save()
        # FIXME: Use transaction to restore DB, wait for mongoengine to
        #   implement it
        except:
            target_course.pull_tags(new_tags, category)
            raise
        target_course.update(push__problems=p.obj)
        self.update(inc__reference_count=1)
        return p.reload()

    def update(self, **ks):
        c = Course(self.course)
        for tag in ks.get('tags', []):
            if not c.check_tag(tag, self.tag_category):
                raise ValueError(
                    'Exist tag that is not allowed to use in this course')
        self.obj.update(**ks)

    def to_dict(self):
        '''
        cast self to python dictionary for serialization
        '''
        ret = self.to_mongo().to_dict()
        ret['pid'] = ret['_id']
        ret['course'] = str(ret['course'])
        ret['attachments'] = [{
            'filename': att.filename,
            'source': str(att.source),
            'version_number': att.version_number,
        } for att in self.attachments]
        ret['timestamp'] = ret['timestamp'].timestamp()
        ret['author'] = self.author.info
        ret['comments'] = [str(c) for c in ret['comments']]
        for k in ('_id', 'height'):
            del ret[k]
        if self.is_OJ:
            for k in ('input', 'output'):
                del ret['extra'][k]
        return ret

    @doc_required('user', 'user', User)
    def to_dict_without_others_OJ(self, user: User):
        ret = self.to_dict()
        if self.is_OJ:
            ret['comments'] = list(
                str(c.id) for c in self.comments if user == c.author)
        return ret

    def acceptance(self, user: User):
        user_comments = (c for c in self.comments if user.obj == c.author)
        acceptance = [c.acceptance for c in user_comments]
        if len(acceptance) == 0:
            return engine.Comment.Acceptance.NOT_TRY
        else:
            return min(acceptance)

    def delete(self):
        '''
        delete the problem
        '''
        # delete attachments
        for a in self.attachments:
            a.delete()
        # remove problem document
        self.obj.delete()

    def insert_attachment(self, file_obj, filename, source=None):
        '''
        insert a attachment into this problem.
        '''
        # check existence
        if any([att.filename == filename for att in self.attachments]):
            raise FileExistsError(
                f'A attachment named [{filename}] '
                'already exists!', )
        # create a new attachment
        att = self.new_attachment(file_obj, filename=filename, source=source)
        # push into problem
        self.attachments.append(att)
        self.save()

    def remove_attachment(self, filename):
        '''
        Remove a attachment by filename.
        Due to the mongoengine's bug, we can not use pull
        operator here, this may cause race condition. DON'T
        call this concurrently.
        '''
        # search by name
        for i, att in enumerate(self.attachments):
            if att.filename == filename:
                # delete it and pop from list
                att.delete()
                self.attachments.pop(i)
                self.save()
                return True
        raise FileNotFoundError(
            f'can not find a attachment named [{filename}]')

    def update_attachment(self, filename):
        # search by name
        for att in self.attachments:
            if att.filename == filename:
                if att.source is None:
                    raise FileNotFoundError(
                        f'attachment named [{filename}] doesn\'t have a source'
                    )
                att.version_number = att.source.version_number
                att.file.replace(att.source.file, filename=filename)
                self.save()
                return True
        raise FileNotFoundError(
            f'can not find a attachment named [{filename}]')

    def rejudge(self):
        from .comment import Comment
        for comment in self.comments:
            Comment(comment).submit()

    def get_file(self):
        # Extract problem attachments
        files = [(
            'attachments',
            (a.filename, a.file),
        ) for a in self.attachments]

        # Attatch standard input / output
        if self.is_OJ:
            with tempfile.NamedTemporaryFile('wb+') as tmp_f:
                with ZipFile(tmp_f, 'w') as zf:
                    # Add multiple files to the zip
                    zf.writestr('input', self.extra.input)
                    zf.writestr('output', self.extra.output)
                tmp_f.seek(0)
                files.append(('testcase', (
                    tmp_f.name,
                    io.BytesIO(tmp_f.read()),
                )))

        return files

    @classmethod
    def filter(
        cls,
        offset: int = 0,
        count: int = -1,
        name: Optional[str] = None,
        course: Optional[str] = None,
        tags: Optional[List[str]] = None,
        only: Optional[List[str]] = None,
        is_template: Optional[bool] = None,
        allow_multiple_comments: Optional[bool] = None,
        type: Optional[str] = None,
    ) -> List[engine.Problem]:
        '''
        read a list of problem filtered by given paramter
        '''
        qs = {
            'course': course,
            'is_template': is_template,
            'allow_multiple_comments': allow_multiple_comments,
        }
        # filter None parameter
        qs = {k: v for k, v in qs.items() if v is not None}
        ps = cls.engine.objects(**qs)
        # filter tags
        if tags is not None:
            ps = ps.filter(
                reduce(
                    lambda x, y: x & y,
                    (Q(tags=t) for t in tags),
                ))
        # Filter problem type
        if type is not None:
            ps = ps.filter(Q(__raw__={'extra._cls': type}))
        # TODO: Support fuzzy search
        # search for title
        if name is not None:
            ps = ps.filter(title__icontains=name)
        # retrive fields
        if only is not None:
            ps = ps.only(*only)
        ps = ps.order_by('pid')[offset:]
        count = len(ps) if count == -1 else count
        return ps[:count]

    @classmethod
    def new_attachment(cls, file_obj, source: engine.Attachment, **ks):
        '''
        create a new attachment, ks will be passed
        to `GridFSProxy`
        '''
        att = GridFSProxy()
        att_ks = {'file': att}
        if source is not None:
            att_ks['source'] = source
            file_obj = source.file
            att_ks['version_number'] = source.version_number
            source.update(inc__quote_count=1)
        att.put(file_obj, **ks)
        return engine.Problem.ProblemAttachment(**att_ks)

    @classmethod
    def copy_attachment(cls, source: engine.Problem.ProblemAttachment):
        '''
        copy an existed attachment
        '''
        att = GridFSProxy()
        att.put(source.file, filename=source.filename)
        return engine.Problem.ProblemAttachment(
            file=att,
            source=source.source,
            version_number=source.version_number,
        )

    @classmethod
    @doc_required('author', 'author', User)
    @doc_required('course', 'course', Course)
    def add(
        cls,
        author: User,
        course: Course,
        tags: List[str] = [],
        **ks,
    ) -> 'Problem':
        '''
        add a problem to db
        '''
        # user needs to be able to modify the course
        if not course.permission(
                user=author,
                req=Course.Permission.PARTICIPATE,
        ):
            raise PermissionError('Not enough permission')
        # if allow_multiple_comments is None or False
        if author < 'teacher' and not ks.get('allow_multiple_comments'):
            raise PermissionError('Students have to allow multiple comments')
        is_oj = ks.get('extra', {}).get('_cls', '') == 'OJ'
        category = engine.Tag.Category.OJ_PROBLEM if is_oj else engine.Tag.Category.NORMAL_PROBLEM
        if not all(course.check_tag(tag, category) for tag in tags):
            raise TagNotFoundError(
                'Exist tag that is not allowed to use in this course')
        # insert a new problem into DB
        p = cls.engine(
            author=author.pk,
            course=course.pk,
            tags=tags,
            **ks,
        ).save()
        # update reference
        course.update(push__problems=p)
        author.update(push__problems=p)
        return cls(p)
