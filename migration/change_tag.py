from mongo.config import config
from pymongo import MongoClient

client = MongoClient(config['MONGO']['HOST'])
db = client[config['MONGO']['DB']]

tags = list(db['tag'].find())
for tag in tags:
    db['tag'].update_one(
        {'_id': tag['_id']},
        {
            '$set': {
                'categories': [1, 2, 3]
            },
        },
    )

# Simple validation
from mongo import engine
for t in engine.Tag.objects():
    t.validate()
