from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os
import pika
import json

app = Flask(__name__)

# Config
MYSQL_USER = os.getenv('MYSQL_USER', 'admin')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password123')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql-svc')
MYSQL_DB = os.getenv('MYSQL_DB', 'enterprise_db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'

db = SQLAlchemy(app)
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq-svc')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20), default='User')
    permissions = db.Column(db.String(50), default='View')

def init_admin():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        new_admin = User(
            username='admin',
            email='admin@devops.com',
            password=generate_password_hash('admin', method='scrypt'),
            role='admin',
            permissions='Admin'
        )
        db.session.add(new_admin)
        db.session.commit()
        print(" [SYSTEM] Default Admin Initialized (admin/admin)")

from mq_helper import publish_event

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    new_user = User(
        username=data['username'],
        email=data['email'],
        password=generate_password_hash(data['password'], method='scrypt')
    )
    db.session.add(new_user)
    db.session.commit()
    publish_event("register", {"username": data['username'], "email": data['email']})
    return jsonify({"message": "User registered successfully"}), 201

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_admin()
    app.run(host='0.0.0.0', port=5000)
