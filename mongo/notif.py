from . import engine
from .base import MongoBase

__all__ = ['Notif']


class Notif(MongoBase, engine=engine.Notif):
    types = engine.Notif.Type

    @classmethod
    def new(cls, info):
        notif = cls.engine(info=info).save()
        return cls(notif)

    def read(self):
        if self.status == engine.Notif.Status.UNREAD:
            self.update(status=engine.Notif.Status.READ)
            self.reload()

    def hide(self):
        if self.status != engine.Notif.Status.HIDDEN:
            self.update(status=engine.Notif.Status.HIDDEN)
            self.reload()

    def to_dict(self):
        return self.info.to_dict()
