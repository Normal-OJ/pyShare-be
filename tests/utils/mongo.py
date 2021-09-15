from mongo.config import config
from mongoengine import connect, disconnect


def drop_db():
    HOST = config['MONGO']['HOST']
    DB = config['MONGO']['DB']
    disconnect()
    conn = connect(
        db=DB,
        host=HOST,
    )
    conn.drop_database(DB)
