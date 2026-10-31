"""DB-free tests for POST /auth/register: the auth_method written must fit the enum.

Prod enum auth_method is {google, password} (migrations/schema.sql); writing
anything else is a 22P02 and a 500.
"""

from unittest import mock

from flask import Flask

from toms_gym.routes import auth_routes

AUTH_METHOD_ENUM = {"google", "password"}
NEW_ID = "44444444-4444-4444-4444-444444444444"


def _app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['JWT_SECRET_KEY'] = 'test-secret'
    app.register_blueprint(auth_routes.auth_bp, url_prefix='/auth')
    return app


def _register(body):
    session = mock.MagicMock()
    session.execute.return_value.fetchone.side_effect = [None, (NEW_ID,)]
    with mock.patch.object(auth_routes, 'get_db_connection', return_value=session), \
         mock.patch.object(auth_routes, 'create_access_token', return_value='tok'), \
         mock.patch.object(auth_routes.SecurityAudit, 'log_auth_event'):
        resp = _app().test_client().post('/auth/register', json=body)
    insert_params = session.execute.call_args_list[1].args[1]
    return resp, insert_params


def test_register_without_password_writes_null_auth_method():
    resp, params = _register({"email": "nopass@example.com", "name": "No Pass"})
    assert resp.status_code == 201
    assert resp.get_json()["user_id"] == NEW_ID
    assert params["password"] is None
    assert params["auth_method"] is None


def test_register_with_password_writes_password_auth_method():
    resp, params = _register({"email": "pw@example.com", "name": "Pw", "password": "Str0ng!Passw0rd#"})
    assert resp.status_code == 201
    assert params["auth_method"] == "password"
    assert params["password"]


def test_every_auth_method_written_fits_the_enum():
    for body in ({"email": "a@example.com", "name": "A"},
                 {"email": "b@example.com", "name": "B", "password": "Str0ng!Passw0rd#"}):
        _, params = _register(body)
        assert params["auth_method"] is None or params["auth_method"] in AUTH_METHOD_ENUM
