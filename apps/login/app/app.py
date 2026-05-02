from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
import os
import redis
import json

app = Flask(__name__)

# Config
MYSQL_USER = os.getenv('MYSQL_USER', 'admin')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password123')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql-svc')
MYSQL_DB = os.getenv('MYSQL_DB', 'enterprise_db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'

db = SQLAlchemy(app)
cache = redis.Redis(host=os.getenv('REDIS_HOST', 'redis-svc'), port=6379, decode_responses=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20), default='User')
    permissions = db.Column(db.String(50), default='View')

from mq_helper import publish_event

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password, data['password']):
        session_data = {"user_id": user.id, "role": user.role, "permissions": user.permissions}
        cache.set(f"session_{user.id}", json.dumps(session_data), ex=3600)
        publish_event("login", {"user_id": user.id, "email": user.email})
        return jsonify({"message": "Login successful", "user_id": user.id, "role": user.role, "permissions": user.permissions})
    return jsonify({"error": "Invalid credentials"}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
