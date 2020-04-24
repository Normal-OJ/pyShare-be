from . import auth
from . import problem
from . import submission
from . import test
from . import user
from . import comment

from .auth import *
from .problem import *
from .submission import *
from .test import *
from .user import *
from .comment import *

__all__ = [
    *auth.__all__,
    *problem.__all__,
    *submission.__all__,
    *test.__all__,
    *user.__all__,
    *comment.__all__,
]
