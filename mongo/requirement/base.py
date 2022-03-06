from datetime import datetime
from mongo import engine
from mongo.base import MongoBase
from typing import Optional


def default_on_task_time_changed(
    cls,
    task,
    old_starts_at: Optional[datetime] = None,
    old_ends_at: Optional[datetime] = None,
):
    '''
    Default implementation of on_task_time_changed.
    '''
    if old_starts_at is None:
        old_starts_at = task.starts_at
    if old_ends_at is None:
        old_ends_at = task.ends_at
    # use list() because filter object can only be iterated once
    reqs = list(
        filter(
            lambda r: isinstance(r, cls.engine),
            task.requirements,
        ))
    if task.starts_at > old_starts_at or task.ends_at < old_ends_at:
        for req in reqs:
            req.update(records={})
            req.reload()
            cls(req).sync(
                starts_at=task.starts_at,
                ends_at=task.ends_at,
            )
    else:
        if task.starts_at < old_starts_at:
            for req in reqs:
                cls(req).sync(
                    starts_at=task.starts_at,
                    ends_at=old_starts_at,
                )
        if task.ends_at > old_ends_at:
            for req in reqs:
                cls(req).sync(
                    starts_at=old_ends_at,
                    ends_at=task.ends_at,
                )


class Requirement(MongoBase, engine=engine.Requirement):
    pass
