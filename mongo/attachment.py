from __future__ import annotations
from typing import Optional
from datetime import datetime
import enum
from . import engine
from .base import MongoBase
from .engine import GridFSProxy
from .utils import doc_required
from .user import User
from .tag import Tag
from .notif import Notif

__all__ = ['Attachment']


class Attachment(MongoBase, engine=engine.Attachment):
    class Permission(enum.Flag):
        WRITE = enum.auto()

    @doc_required('user', User)
    def own_permission(self, user: User) -> 'Attachment.Permission':
        _permission = self.Permission(0)
        # problem author and admin can edit, delete attachment
        if user == self.author or user >= 'admin':
            _permission |= self.Permission.WRITE
        return _permission

    @doc_required('user', 'user', User)
    def permission(self, user: User, req) -> bool:
        '''
        check user's permission, `req` is a set of required
        permissions

        Returns:
            a `bool` value denotes whether user has these
            permissions 
        '''
        _permission = self.own_permission(user=user)
        return bool(req & _permission)

    def delete(self):
        '''
        remove an attachment from db
        '''
        self.file.delete()
        self.obj.delete()

    def update(
        self,
        filename: str,
        file_obj,
        description: str,
        patch_note: str,
        tags_str: str,
    ):
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
    def to_tag_list(cls, tags_str: Optional[str]):
        if tags_str == '' or tags_str is None:
            return False
        tags = tags_str.split(',')
        if not all(
                Tag.is_tag(tag, engine.Tag.Category.ATTACHMENT)
                for tag in tags):
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
