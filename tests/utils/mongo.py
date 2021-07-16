from mongoengine import connect, disconnect

MONGO_HOST = 'mongomock://localhost'
DB = 'pyShare'


def drop_db():
    disconnect()
    conn = connect(
        db=DB,
        host=MONGO_HOST,
    )
    conn.drop_database(DB)
