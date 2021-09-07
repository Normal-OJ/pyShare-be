from flask.testing import FlaskClient
from mongo import *
from tests import utils


class TestFakeProdEnv:
    @classmethod
    def setup_class(cls):
        from mongo.config import config
        config.DEBUG = False

    def test_no_dummy_api_under_prod_config(self, config_client):
        client = config_client()
        assert client.application.config['DEBUG'] == False
        rv = client.get('/dummy')
        assert rv.status_code == 404
