from functools import wraps
from flask_socketio import Namespace, emit, send, join_room, leave_room
import json

__all__ = ['fe_update', 'Notifier']


class Notifier(Namespace):
    namespace = '/notifier'

    def on_subscribe(self, data):
        room = f"{data['topic']}-{data['id']}"
        join_room(room)

    def on_unsubscribe(self, data):
        room = f"{data['topic']}-{data['id']}"
        leave_room(room)


def uriparser(obj, *uris):
    def resolver(o, uri):
        for u in uri.split('/'):
            u = int(u[1:]) if u[0] == ':' and u[1:].isnumeric() else u
            try:
                o = o[u]
            except (IndexError, KeyError, TypeError):
                return None
        return o
    return tuple(resolver(obj, uri) for uri in uris)


def fe_update(topic, *uris):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ret = func(*args, **kwargs)
            data = uriparser(json.loads(ret[0].data), *(f'data/{uri}' for uri in uris))
            pk = '-'.join(map(str, data))
            emit('refetch', {'topic': topic, 'id': pk}, room=f'{topic}-{pk}', namespace=Notifier.namespace)
            return ret
        return wrapper
    return decorator
