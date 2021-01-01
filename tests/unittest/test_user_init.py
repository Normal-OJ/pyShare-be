import pytest
from mongo import *
from mongo import engine
from tests import utils


def setup_function(_):
    utils.mongo.drop_db()


def check_pk(u, username):
    assert u.username == username
    assert u.pk == username


def test_init_anyone_with_username():
    username = 'bogay'
    u = User(username)
    check_pk(u, username)


def test_init_existent_one_with_username():
    username = 'bogay'
    User.signup(**utils.user.data(username=username))
    u = User(username)
    check_pk(u, username)


def test_init_anyone_with_document():
    username = 'bogay'
    u = User(engine.User(username=username))
    check_pk(u, username)


def test_init_existent_one_with_document():
    username = 'bogay'
    User.signup(**utils.user.data(username=username))
    u = User(engine.User(username=username))
    check_pk(u, username)
