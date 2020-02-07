from flask import Flask
from model import *
from mongo import *
from mongo import engine
from mongo import problem

# Create a flask app
app = Flask(__name__)
app.url_map.strict_slashes = False

# Regist flask blueprint
app.register_blueprint(auth_api, url_prefix='/auth')
app.register_blueprint(problem_api, url_prefix='/problem')
app.register_blueprint(test_api, url_prefix='/test')
app.register_blueprint(post_api, url_prefix='/post')
app.register_blueprint(user_api, url_prefix='/user')

if not User("first_admin"):
    ADMIN = {
        'username': 'first_admin',
        'password': 'firstpasswordforadmin',
        'email': 'i.am.first.admin@noj.tw'
    }

    admin = User.signup(**ADMIN)
    admin.update(active=True, role=0)

if Number("serial_number").obj is None:
    engine.Number(name="serial_number").save()

problem.number = Number("serial_number").obj.number
