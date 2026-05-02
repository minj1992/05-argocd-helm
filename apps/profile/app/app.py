from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

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
    username = db.Column(db.String(50))
    email = db.Column(db.String(100))
    role = db.Column(db.String(20))
    permissions = db.Column(db.String(50))

@app.route('/profile/<int:user_id>')
def profile(user_id):
    user = User.query.get(user_id)
    if user:
        return jsonify({
            "username": user.username, 
            "email": user.email,
            "role": user.role,
            "permissions": user.permissions
        })
    return jsonify({"error": "User not found"}), 404

@app.route('/admin/users')
def list_users():
    users = User.query.all()
    return jsonify([{
        "id": u.id, 
        "username": u.username, 
        "email": u.email, 
        "role": u.role, 
        "permissions": u.permissions
    } for u in users])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
