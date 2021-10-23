from mongo.config import config
from pymongo import MongoClient

client = MongoClient(config['MONGO']['HOST'])
db = client[config['MONGO']['DB']]

comments = list(db['comment'].find())
for comment in comments:
    submission_ids = comment['submissions']
    if len(submission_ids) == 0:
        acceptance = 3  # NOT_TRY
    else:
        acceptance = 2  # PENDING
        for id in submission_ids:
            submission = db['submission'].find_one({'_id': id})
            if submission['state'] == 1:  # ACCEPT
                acceptance = 0  # ACCEPTED
                break
            if submission['state'] == 2:  # DENIED
                acceptance = 1  # REJECTED
    db['comment'].update_one(
        {'_id': comment['_id']},
        {
            '$unset': {
                'hasAccepted': ''
            },
            '$set': {
                'acceptance': acceptance
            }
        },
    )

# Simple validation
from mongo import engine
for c in engine.Comment.objects():
    c.validate()
