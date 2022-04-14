from mongo.config import config
from pymongo import MongoClient

client = MongoClient(config['MONGO']['HOST'])
db = client[config['MONGO']['DB']]

problems = list(db['problem'].find())
for problem in problems:
    db['problem'].update_one(
        {'_id': problem['_id']},
        {
            '$unset': {
                'status': ''
            },
            '$set': {
                'hidden': problem['status'] == 0
            },
        },
    )

# Simple validation
from mongo import engine
for p in engine.Problem.objects():
    p.validate()
