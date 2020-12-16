from . import engine
from .base import MongoBase
from .engine import GridFSProxy

__all__ = ['Attachment']


class Attachment(MongoBase, engine=engine.Attachment):
    def __init__(self, filename):
        self.filename = filename

    def copy(self):
        '''
        copy an attachment in db
        '''
        if not self:
            raise FileNotFoundError(
                f'can not find a attachment named [{self.filename}] in public attachment DB'
            )
        return self.file

    def delete(self):
        '''
        remove an attachment from db
        '''
        if not self:
            raise FileNotFoundError(
                f'can not find a attachment named [{self.filename}]')
        self.file.delete()
        self.obj.delete()

    def update(self, file_obj, description):
        '''
        update an attachment from db
        '''
        if not self:
            raise FileNotFoundError(
                f'can not find a attachment named [{self.filename}]')
        if file_obj is not None:
            self.file.replace(file_obj, filename=self.filename)
        self.description = description
        self.save()

    @classmethod
    def add(cls, file_obj, filename, description):
        '''
        add an attachment to db
        '''
        if Attachment(filename):
            raise FileExistsError(
                f'A attachment named [{filename}] '
                'already exists!', )
        file = GridFSProxy()
        file.put(file_obj, filename=filename)

        attachment = engine.Attachment(filename=filename,
                                       file=file,
                                       description=description)
        attachment.save()
