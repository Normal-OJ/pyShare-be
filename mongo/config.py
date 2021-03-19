__all__ = (
    'Config',
    'ProdConfig',
    'ConfigLoader',
)


class Config:
    TESTING = True
    DEBUG = True


class ProdConfig(Config):
    TESTING = False
    DEBUG = False


class ConfigLoader:
    curr_config = Config()

    @classmethod
    def load(cls, config):
        if not issubclass(config, Config):
            raise TypeError
        cls.curr_config = config()

    @classmethod
    def get(cls, key, default=None):
        return getattr(cls.curr_config, key, default)
