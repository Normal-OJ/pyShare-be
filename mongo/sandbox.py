from abc import ABC, abstractmethod
import requests as rq
from . import engine
from .utils import doc_required, logger, drop_none
from .submission import Submission
from .problem import Problem
from .token import Token
from .config import config

__all__ = (
    'ISandbox',
    'Sandbox',
    'SandboxNotFound',
)


class SandboxNotFound(Exception):
    pass


class ISandbox(ABC):
    cls = None

    @abstractmethod
    def send(self, submission: Submission) -> bool:
        raise NotImplementedError

    @classmethod
    def use(cls, _cls):
        if not _cls is None and not issubclass(_cls, ISandbox):
            raise TypeError('It shoud be a subclass of ISandbox or None')
        cls.cls = _cls


# TODO: Inherit MongoBase
class Sandbox(ISandbox):
    def get_loading(self, sandbox: engine.Sandbox) -> float:
        resp = rq.get(f'{sandbox.url}/status')
        if not resp.ok:
            return 1
        return resp.json()['load']

    @doc_required('submission', Submission)
    def send(self, submission: Submission) -> bool:
        try:
            target = min(engine.Sandbox.objects, key=self.get_loading)
        # engine.Sandbox.objects is empty
        except ValueError:
            raise SandboxNotFound
        token = Token(target.token).assign(str(submission.id))
        try:
            resp = rq.post(
                f'{target.url}/{submission.id}',
                files=Problem(submission.problem).get_file(),
                data={
                    'src': submission.code,
                    'token': token,
                },
            )
        except rq.exceptions.RequestException as e:
            logger().error(
                f'Submit error. [target={target.id},'
                f' submission={submission.id}, err={e}]', )
            return False
        else:
            logger().info(f'Submission sent. [id={submission.id}]')
            if not resp.ok:
                logger().warning(f'Got sandbox resp. [resp={resp.text}]')
            return True


def init():
    if 'sandbox' not in config:
        logger().info('No init sandbox set')
        return
    logger().info('Initalize sandbox instance')
    url = config.get('SANDBOX.URL')
    token = config.get('SANDBOX.TOKEN')
    alias = config.get('SANDBOX.ALIAS')
    if url is None or token is None:
        logger().warning('Sandbox url and token are required. Won\'t create')
        return
    args = dict(
        url=url,
        token=token,
        alias=alias,
    )
    sandbox = engine.Sandbox(**drop_none(args)).save()
    logger().info(f'Initial sandbox created. [id={sandbox.id}]')
