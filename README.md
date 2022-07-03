# pyShare backend

[![pipeline status](https://gitlab.com/pyshare/backend/badges/master/pipeline.svg)](https://gitlab.com/pyshare/backend/-/commits/master) [![coverage report](https://gitlab.com/pyshare/backend/badges/master/coverage.svg)](https://gitlab.com/pyshare/backend/-/commits/master)

## Project Structure

This project contains following files (not important files omitted.):

```
.
├── migration                  # DB migration scripts
├── model                      # Web API
├── mongo                      # Domain
├── tests                      # Testcases
├── Dockerfile
├── Dockerfile.prod
├── app.py                     # Project entrypoint
├── requirements.txt           # Production dependencies
├── gunicorn.conf.py
└── settings.yaml
```

The most important parts are
- Web API layer: `model/` & `app.py`
- Domain layer: `mongo/`
So, let me explain next.

### Web API

Most modules inside `model/` represents an RESTful resource, for example, `user.py`
is mapped to `/user` API, and they are registed in `app.py`.

#### Utils

There are some heavily-used APIs in pyShare.

- `Request`
- `login_required`
- `HTTPResponse`
- `HTTPError`

### Domain

*TODO*
