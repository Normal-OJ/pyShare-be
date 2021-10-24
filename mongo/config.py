from dynaconf import Dynaconf, Validator, ValidationError

__all__ = ('ConfigLoader', )

DEFAULT_SECRET = 'SuperSecretString'


# TODO: implement custom validator
def non_dev_check(_config: Dynaconf):
    requireds = (
        'SMTP.SERVER',
        'SMTP.NOREPLY',
        'SMTP.NOREPLY_PASSWORD',
    )
    for req in requireds:
        if _config.get(req) is None:
            raise ValidationError(
                f'{req} are required in env {_config["ENV"]}')
    if _config['JWT']['SECRET'] == DEFAULT_SECRET:
        raise ValidationError(f'Use default secret in env {_config["ENV"]}')
    _config['DEBUG'] = False
    _config['TESTING'] = False


config = Dynaconf(
    envvar_prefix='PYSHARE',
    settings_files=[
        'settings.yaml',
        'settings.prod.yaml',
    ],
    includes=[
        '.secrets.yaml',
    ],
    validators=[
        Validator('ENV', default='development'),
        Validator('JWT.SECRET', default=DEFAULT_SECRET),
        # If no specified, decided by env
        Validator('DEBUG', default=True),
        Validator('TESTING', default=True),
    ],
)

if config['ENV'] != 'development':
    non_dev_check(config)


class ConfigLoader:
    @classmethod
    def get(cls, key, default=None):
        return config.get(key, default)
