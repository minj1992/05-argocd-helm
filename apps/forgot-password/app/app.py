from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os
import time

app = Flask(__name__)

# Config
MYSQL_USER = os.getenv('MYSQL_USER', 'admin')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password123')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql-svc')
MYSQL_DB = os.getenv('MYSQL_DB', 'enterprise_db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'

db = SQLAlchemy(app)

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

from mq_helper import publish_event

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if user:
        user.password = generate_password_hash(data['new_password'], method='scrypt')
        db.session.commit()
        publish_event("password_reset", {"email": data['email']})
        return jsonify({"message": "Password reset successful"})
    return jsonify({"error": "User not found"}), 404

if __name__ == '__main__':
    with app.app_context():
        max_retries = 10
        for i in range(max_retries):
            try:
                db.engine.connect()
                print(" [SYSTEM] Database connected successfully.")
                break
            except Exception as e:
                print(f" [ERROR] DB Connection failed (attempt {i+1}/{max_retries}): {e}")
                time.sleep(10)
    app.run(host='0.0.0.0', port=5000)
