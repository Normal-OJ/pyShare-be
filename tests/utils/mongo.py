from mongo.config import config
from mongo.engine import _connect
from mongoengine import disconnect


def drop_db():
    # TODO: don't directly expose DB variable here
    DB = config['MONGO']['DB']
    disconnect()
    conn = _connect()
    conn.drop_database(DB)
