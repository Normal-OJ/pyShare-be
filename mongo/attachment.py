from . import engine
from .base import MongoBase
from .engine import GridFSProxy

__all__ = ['Attachment']


class Attachment(MongoBase, engine=engine.Attachment):
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
        self.description = description
        self.save()

    @classmethod
    def add(cls, file_obj, filename, description):
        '''
        add an attachment to db
        '''
        if file_obj is None:
            raise FileNotFoundError('you need to upload a file')
        if cls(filename):
            raise FileExistsError(f'{cls(filename)} already exists!')
        # save file
        file = GridFSProxy()
        file.put(file_obj, filename=filename)
        # save attachment
        attachment = cls.engine(
            filename=filename,
            file=file,
            description=description,
        ).save()
        return cls(attachment)
