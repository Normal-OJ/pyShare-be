import os
from mongo.config import config
from pymongo import MongoClient

client = MongoClient(config['MONGO']['HOST'])
db = client[config['MONGO']['DB']]
# Update problem attachments
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
# Update submission
db['submission'].update_many({}, {'$set': {'_cls': 'Submission'}})
db['submission'].update_many(
    {
        'status': {
            '$nin': [0, 1, 2]
        },
    },
    {
        '$set': {
            'status': 0
        },
    },
)
# Simple validation
from mongo import engine
for p in engine.Problem.objects():
    p.validate()
for s in engine.Submission.objects():
    s.validate()
