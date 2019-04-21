import os
import boto3
from chalice import Chalice, AuthResponse
from chalicelib.db import DynamoDBTodo
from chalicelib import auth

app = Chalice(app_name='mytodo')
app.debug = True
_DB = None
_USER_DB = None


def get_app_db():
    global _DB
    if _DB is None:
        _DB = DynamoDBTodo(
            boto3.resource('dynamodb').Table(
                os.environ['APP_TABLE_NAME']
            )
        )
    return _DB


def get_users_db():
    global _USER_DB
    if _USER_DB is None:
        _USER_DB = boto3.resource('dynamodb').Table(
            os.environ['USERS_TABLE_NAME']
        )
    return _USER_DB


def get_authorized_username(current_request):
    return current_request.context['authorizer']['principalId']


@app.authorizer()
def jwt_auth(auth_request):
    token = auth_request.token
    decoded = auth.decode_jwt_token(token)
    return AuthResponse(routes=['*'], principal_id=decoded['sub'])


@app.route('/todos', methods=['GET'], authorizer=jwt_auth)
def get_todos():
    username = get_authorized_username(app.current_request)
    return get_app_db().list_items(username=username)


@app.route('/todos', methods=['POST'], authorizer=jwt_auth)
def add_new_todo():
    body = app.current_request.json_body
    username = get_authorized_username(app.current_request)
    return get_app_db().add_item(
        username=username,
        description=body['description'],
        metadata=body['metadata']
    )


@app.route('/todos/{uid}', methods=['GET'],  authorizer=jwt_auth)
def get_todo(uid):
    username = get_authorized_username(app.current_request)
    return get_app_db().get_item(uid, username=username)


@app.route('/todos/{uid}', methods=['DELETE'], authorizer=jwt_auth)
def delete_todo(uid):
    username = get_authorized_username(app.current_request)
    return get_app_db().delete_item(uid, username=username)


@app.route('/todos/{uid}', methods=['PUT'], authorizer=jwt_auth)
def update_todo(uid):
    username = get_authorized_username(app.current_request)
    body = app.current_request.json_body
    get_app_db().update_item(
        uid,
        description=body['description'],
        state=body['state'],
        metadata=body['metadata'])

@app.route('/login', methods=['POST'])
def login():
    body = app.current_request.json_body
    record = get_users_db().get_item(
        Key={'username': body['username']}
    )['Item']
    jwt_token = auth.get_jwt_token(
        body['username'], body['password'], record
    )
    return {'token': jwt_token.decode('utf-8')}
