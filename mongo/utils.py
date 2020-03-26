import hashlib
from functools import wraps

__all__ = ['hash_id', 'doc_required']


def hash_id(salt, text):
    text = ((salt or '') + (text or '')).encode()
    sha = hashlib.sha3_512(text)
    return sha.hexdigest()[:24]


def doc_required(src, des, cls):
    '''
    query db to inject document into functions.
    if the document does not exist in db, raise `engine.DoesNotExist`.
    if `src` not in parameters, this funtcion will raise `TypeError`
    `doc_required` will check the existence of `des` in `func` parameters,
    if `des` is exist, this function will override it, so `src == des`
    are acceptable
    '''
    def deco(func):
        @wraps(func)
        def wrapper(*args, **ks):
            # try get source param
            src_param = ks.get(src)
            if src_param is None:
                raise TypeError(f'{src} not found in function argument')
            # convert it to document
            if not isinstance(src_param, cls):
                doc = cls(src_param)
            # or, it is already target class instance
            else:
                doc = src_param
            if not doc:
                raise engine.DoesNotExist(doc)
            # replace original paramters
            del ks[src]
            if des in ks:
                current_app.logger.warning(
                    f'replace a existed argument in {func}')
            ks[des] = doc
            return func(*args, **ks)

        return wrapper

    return deco