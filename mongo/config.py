from dynaconf import Dynaconf, Validator, ValidationError

__all__ = ('ConfigLoader', )

DEFAULT_SECRET = 'SuperSecretString'
config = Dynaconf(
    envvar_prefix='PYSHARE',
    settings_files=[
        'settings.yaml',
        'settings.prod.yaml',
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

# TODO: implement custom validator
if config['ENV'] != 'development':
    requireds = (
        'SMTP.SERVER',
        'SMTP.NOREPLY',
        'SMTP.NO_REPLY_PASSWORD',
    )
    for req in requireds:
        if config.get(req) is None:
            raise ValidationError(f'{req} are required in env {config["ENV"]}')
    if config['JWT']['SECRET'] == DEFAULT_SECRET:
        raise ValidationError(f'Use default secret in env {config["ENV"]}')
    config['DEBUG'] = False
    config['TESTING'] = False


class ConfigLoader:
    @classmethod
    def get(cls, key, default=None):
        return config.get(key, default)
