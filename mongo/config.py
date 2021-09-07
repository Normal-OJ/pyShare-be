from dynaconf import Dynaconf, Validator

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
        #     Validator('MONGO.DB', default='pyShare'),
        #     Validator(
        #         'MONGO.HOST',
        #         env='production',
        #         must_exist=True,
        #     ),
        #     Validator(
        #         'MONGO.HOST',
        #         default='mongomock://localhost',
        #         env='development',
        #     ),
        #     Validator(
        #         'REDIS.HOST',
        #         'REDIS.PORT',
        #         must_exist=True,
        #         env='production',
        #     ),
        #     Validator('JWT.EXP', default='30'),
        #     Validator('JWT.ISS', default='test.test'),
        #     # Don't use default secret under production mode
        #     Validator(
        #         'JWT.SECRET',
        #         env='production',
        #         ne='SuperSecretString',
        #     ),
        Validator('JWT.SECRET', default=DEFAULT_SECRET),
        #     Validator(
        #         'SMTP.SERVER',
        #         'SMTP.ADMIN',
        #         'SMTP.ADMIN_PASSWORD',
        #         'SMTP.NOREPLY',
        #         'SMTP.NO_REPLY_PASSWORD',
        #         env='production',
        #         must_exist=True,
        #     ),
        # If no specified, decided by env
        Validator('DEBUG',
                  default=lambda setting, _: setting.ENV != 'production'),
        Validator('TESTING',
                  default=lambda setting, _: setting.ENV != 'production'),
    ],
)


class ConfigLoader:
    @classmethod
    def get(cls, key, default=None):
        return config.get(key, default)
