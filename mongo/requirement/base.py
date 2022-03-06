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


def default_on_task_time_changed(
    cls,
    task,
    old_starts_at: datetime,
    old_ends_at: datetime,
):
    '''
    Default implementation of on_task_time_changed.
    '''
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
