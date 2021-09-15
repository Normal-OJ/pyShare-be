from . import engine
from .base import MongoBase
from .engine import GridFSProxy
from datetime import datetime
from .utils import doc_required
from .user import User
from .tag import Tag
from .notif import Notif

__all__ = ['Attachment']


class Attachment(MongoBase, engine=engine.Attachment):
    @doc_required('user', 'user', User)
    def own_permission(self, user: User):
        '''
        {'w'}
        represent modify
        '''
        _permission = set()
        # problem author and admin can edit, delete attachment
        if user == self.author or user >= 'admin':
            _permission |= {'w'}
        return _permission

    @doc_required('user', 'user', User)
    def permission(self, user: User, req):
        '''
        check user's permission, `req` is a set of required
        permissions

        Returns:
            a `bool` value denotes whether user has these
            permissions 
        '''
        _permission = self.own_permission(user=user)
        if isinstance(req, set):
            return not bool(req - _permission)
        return req in _permission

    def delete(self):
        '''
        remove an attachment from db
        '''
        self.file.delete()
        self.obj.delete()

    def update(self, filename, file_obj, description, patch_note, tags_str):
        '''
        update an attachment from db
        '''
        tags = self.to_tag_list(tags_str)
        if tags:
            self.tags = tags
        if file_obj is not None:
            self.file.replace(file_obj, filename=self.filename)
            self.size = file_obj.getbuffer().nbytes
        self.description = description
        self.filename = filename
        self.updated = datetime.now()
        self.patch_notes.append(patch_note)
        self.save()

        # TODO: make query faster
        for problem in engine.Problem.objects(attachments__source=self.obj):
            for attachment in problem.attachments:
                if self == attachment.source:
                    info = Notif.types.AttachmentUpdate(
                        attachment=self.obj,
                        problem=problem,
                        name=attachment.filename,
                    )
                    notif = Notif.new(info)
                    problem.author.update(push__notifs=notif.pk)

    @classmethod
    def to_tag_list(cls, tags_str):
        if tags_str == '' or tags_str is None:
            return False
        tags = tags_str.split(',')
        if not all(map(Tag, tags)):
            raise engine.DoesNotExist
        return tags

    @classmethod
    @doc_required('author', User)
    def add(
        cls,
        author: User,
        file_obj,
        filename: str,
        description: str,
        patch_note: str,
        tags_str: str,
    ):
        '''
        add an attachment to db
        '''
        if author < 'teacher':
            raise PermissionError('students can\'t creat attachments', )
        if file_obj is None:
            raise FileNotFoundError('you need to upload a file')
        tags = cls.to_tag_list(tags_str)
        if not tags:
            tags = []
        # save file
        file = GridFSProxy()
        file.put(file_obj, filename=filename)

        # save attachment
        attachment = cls.engine(
            filename=filename,
            file=file,
            description=description,
            updated=datetime.now(),
            created=datetime.now(),
            author=author.pk,
            size=file_obj.getbuffer().nbytes,
            patch_notes=[patch_note],
            tags=tags,
        ).save()
        return cls(attachment)
