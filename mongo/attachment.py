from . import engine
from .base import MongoBase
from .engine import GridFSProxy
from datetime import datetime
from .utils import doc_required
from .user import User

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

    def copy(self):
        '''
        copy an attachment in db
        '''
        if not self:
            raise FileNotFoundError(
                f'can not find {self} in public attachment DB')
        return self.file

    def delete(self):
        '''
        remove an attachment from db
        '''
        self.file.delete()
        self.obj.delete()

    def update(self, file_obj, description):
        '''
        update an attachment from db
        '''
        if file_obj is not None:
            self.file.replace(file_obj, filename=self.filename)
            self.size = file_obj.getbuffer().nbytes
        self.description = description
        self.updated = datetime.now()
        self.save()

    @classmethod
    @doc_required('author', User)
    def add(cls, author: User, file_obj, filename, description):
        '''
        add an attachment to db
        '''
        if file_obj is None:
            raise FileNotFoundError('you need to upload a file')
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
        ).save()
        return cls(attachment)
