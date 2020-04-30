import time
import json
from functools import wraps
from flask import request, current_app

# from model import *
from mongo import *
from mongo import engine
from .response import *

__all__ = ['Request', 'timing_request']

type_map = {
    'int': int,
    'list': list,
    'str': str,
    'dict': dict,
    'bool': bool,
    'None': type(None)
}


class _Request(type):
    def __getattr__(self, content_type):
        def get(*keys, vars_dict={}):
            def data_func(func):
                @wraps(func)
                def wrapper(*args, **kwargs):
                    data = getattr(request, content_type)
                    if data == None:
                        return HTTPError(
                            f'Unaccepted Content-Type {content_type}', 415)
                    try:
                        # Magic
                        # yapf: disable
                        kwargs.update({
                            k: (lambda v: v
                                if t is None or type(v) is t else int(''))(
                                    data.get((lambda s, *t: s + ''.join(
                                        map(str.capitalize, t))
                                              )(*filter(bool, k.split('_')))))
                            for k, t in map(
                                lambda x:
                                (x[0], (x[1:] or None) and type_map.get(x[1].strip())),
                                map(lambda q: q.split(':', 1), keys))
                        })
                        # yapf: enable
                    except ValueError as ve:
                        return HTTPError('Requested Value With Wrong Type',
                                         400)
                    kwargs.update(
                        {v: data.get(vars_dict[v])
                         for v in vars_dict})
                    return func(*args, **kwargs)

                return wrapper

            return data_func

        return get


class Request(metaclass=_Request):
    @staticmethod
    def doc(src, des, cls=None):
        '''
        a warpper to `doc_required` for flask route
        '''
        def deco(func):
            @wraps(func)
            @doc_required(src, des, cls)
            def wrapper(*args, **ks):
                try:
                    return func(*args, **ks)
                # if document not exists in db
                except engine.DoesNotExist as e:
                    return HTTPError(str(e), 404)
                # if args missing
                except TypeError as e:
                    return HTTPError(str(e), 500)

            return wrapper

        return deco


def timing_request(func):
    '''
    inject the execution time into response
    the func must return a response with json
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        # calculate execution time
        # and get the response
        start = time.time()
        resp, status_code = func(*args, **kwargs)
        exec_time = f'{time.time() - start:.2f}s'
        # load response data
        data = resp.data
        data = json.loads(data)
        # inject execution time into response
        if data['data'] is None:
            data['data'] = {}
        data['data'].update({'__execTime': exec_time})
        # make response
        resp.data = json.dumps(data)
        return resp, status_code

    return wrapper
