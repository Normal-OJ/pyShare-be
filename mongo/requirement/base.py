from datetime import datetime
from mongo import engine
from mongo.base import MongoBase


def default_on_task_due_extended(
    cls,
    task,
    starts_at: datetime,
):
    '''
    Default implementation of on_task_due_extended.
    '''
    reqs = filter(
        lambda r: isinstance(r, cls.engine),
        task.requirements,
    )
    for req in reqs:
        cls(req).sync(
            starts_at=starts_at,
            ends_at=task.ends_at,
        )


class Requirement(MongoBase, engine=engine.Requirement):
    def get_cls(self):
        from . import LeaveComment, LikeOthersComment, ReplyToComment, SolveOJProblem
        cls_table = {
            'LeaveComment': LeaveComment,
            'LikeOthersComment': LikeOthersComment,
            'ReplyToComment': ReplyToComment,
            'SolveOJProblem': SolveOJProblem,
        }
        return cls_table[self._cls.split('.')[-1]](self.obj)
