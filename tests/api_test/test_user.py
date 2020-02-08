def test_get_all_user(config_client):
    client = config_client(env='default_user')
    rv = client.get('/user')
    rv_json = rv.json
    assert rv.status_code == 200, rv_json
    assert len(rv_json['data']) == 3