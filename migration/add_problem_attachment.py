import os
from pymongo import MongoClient

client = MongoClient(os.getenv('MONGO_HOST'))
db = client['pyShare']
attachments = {}
for problem in db['problem'].find():
    attachments[problem['_id']] = [{
        'file': atta
    } for atta in problem['attachments']]
for _id, attas in attachments.items():
    db['problem'].update_one(
        {'_id': _id},
        {'$set': {
            'attachments': attas
        }},
    )

# Simple validation
from mongo import engine
for p in engine.Problem.objects():
    p.validate()
