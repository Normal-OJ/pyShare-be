from . import engine
from .base import MongoBase
from .engine import GridFSProxy

__all__ = ['Attachment']


class Attachment(MongoBase, engine=engine.Attachment):
    def __init__(self, filename):
        self.name = filename

    def delete(self):
        '''
        remove an attachment from db
        '''
        attachment = engine.Attachment.objects(file__filename=self.filename)
        if not attachment:
            raise FileNotFoundError(f'can not find a attachment named [{self.filename}]')
        attachment.file.delete()
        self.obj.delete()

    @classmethod
    def add(cls, file_obj, filename, description):
        '''
        add an attachment to db
        '''
        if engine.Attachment.objects(file__filename=filename):
            raise FileExistsError(
                f'A attachment named [{filename}] '
                'already exists!', )
        file = GridFSProxy()
        file.put(file_obj, filename=filename)

        attachment = engine.Attachment(file=file, description=description)
        attachment.save()
