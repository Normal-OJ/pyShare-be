from bson import ObjectId
from flask import jsonify, redirect, json, Response
from mongo import ObjectIdEncoder

__all__ = (
    'HTTPResponse',
    'HTTPRedirect',
    'HTTPError',
    'PyShareJSONEncoder',
)


class PyShareJSONEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return ObjectIdEncoder().default(o)
        except TypeError:
            return super().default(o)


class HTTPBaseResponese(tuple):
    def __new__(
        cls,
        resp: Response,
        status_code: int = 200,
        cookies: dict = {},
    ):
        for c in cookies:
            if cookies[c] == None:
                resp.delete_cookie(c)
            else:
                d = c.split('_httponly')
                resp.set_cookie(d[0], cookies[c], httponly=bool(d[1:]))
        return super().__new__(tuple, (resp, status_code))


class HTTPResponse(HTTPBaseResponese):
    def __new__(
        cls,
        message: str = '',
        status_code: int = 200,
        status: str = 'ok',
        data=None,
        cookies: dict = {},
    ):
        resp = jsonify({
            'status': status,
            'message': str(message),
            'data': data,
        })
        return super().__new__(HTTPBaseResponese, resp, status_code, cookies)


class HTTPRedirect(HTTPBaseResponese):
    def __new__(cls, location, status_code=302, cookies={}):
        resp = redirect(location)
        return super().__new__(HTTPBaseResponese, resp, status_code, cookies)


class HTTPError(HTTPResponse):
    def __new__(
        cls,
        message,
        status_code: int,
        data=None,
        logout: bool = False,
    ):
        cookies = {'piann': None, 'jwt': None} if logout else {}
        return super().__new__(
            HTTPResponse,
            message,
            status_code,
            'err',
            data,
            cookies,
        )
