from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, Response
import requests
import os
import redis
import mysql.connector
import json
import markdown
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'enterprise-frontend-secret')

# Infrastructure Config
REDIS_HOST = os.getenv('REDIS_HOST', 'redis-svc')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql-svc')
MYSQL_USER = os.getenv('MYSQL_USER', 'admin')
MYSQL_PASS = os.getenv('MYSQL_PASSWORD', 'password123')
MYSQL_DB = os.getenv('MYSQL_DB', 'enterprise_db')
RABBITMQ_MGMT_URL = os.getenv('RABBITMQ_MGMT_URL', 'http://rabbitmq-svc:15672/api/queues')

# Service URLs
LOGIN_URL = os.getenv('LOGIN_URL', 'http://login-service-svc/login')
REGISTER_URL = os.getenv('REGISTER_URL', 'http://register-service-svc/register')
PROFILE_URL = os.getenv('PROFILE_URL', 'http://profile-service-svc/profile')
ADMIN_USERS_URL = os.getenv('ADMIN_USERS_URL', 'http://profile-service-svc/admin/users')
FORGOT_PASSWORD_URL = os.getenv('FORGOT_PASSWORD_URL', 'http://forgot-password-service-svc/reset-password')
LOGOUT_URL = os.getenv('LOGOUT_URL', 'http://logout-service-svc/logout')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Access Denied: Admin Rights Required')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def get_redis_client():
    return redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            resp = requests.post(LOGIN_URL, json={"email": email, "password": password}, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                session['user_id'] = data['user_id']
                session['role'] = data['role']
                session['permissions'] = data['permissions']
                return redirect(url_for('dashboard'))
            flash('Invalid credentials.')
        except:
            flash('Login Service Offline')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    r = get_redis_client()
    audit_logs = [json.loads(log) for log in r.lrange("enterprise_audit_log", 0, 29)]
    cache_info = r.info()
    
    mq_stats = {"messages_total": 0}
    try:
        mq_resp = requests.get(RABBITMQ_MGMT_URL, auth=('guest', 'guest'), timeout=2)
        if mq_resp.status_code == 200:
            mq_stats["messages_total"] = sum([q.get('messages', 0) for q in mq_resp.json()])
    except: pass

    return render_template('dashboard.html', audit_logs=audit_logs, cache_info=cache_info, mq_stats=mq_stats)

@app.route('/admin/users')
@login_required
@admin_required
def manage_users():
    try:
        resp = requests.get(ADMIN_USERS_URL, timeout=5)
        users = resp.json()
    except:
        users = []
    return render_template('user_management.html', users=users)

@app.route('/stream-logs/<service>')
@login_required
def stream_logs(service):
    def generate():
        r = get_redis_client()
        # Filter audit logs for the specific service
        logs = r.lrange("enterprise_audit_log", 0, 50)
        for log in logs:
            log_data = json.loads(log)
            if service == 'all' or service in log_data['routing_key']:
                yield f"data: {json.dumps(log_data)}\n\n"
    return Response(generate(), mimetype='text/event-stream')

@app.route('/download-logs')
@login_required
def download_logs():
    r = get_redis_client()
    logs = r.lrange("enterprise_audit_log", 0, -1)
    content = "\n".join(logs)
    return Response(content, mimetype="text/plain", headers={"Content-disposition": "attachment; filename=enterprise_logs.txt"})

@app.route('/architecture')
@login_required
def architecture():
    try:
        with open('/data/lab.md', 'r') as f: content = f.read()
    except: content = "# Architecture Guide\nNotFound"
    html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
    return render_template('architecture.html', content=html_content)

@app.route('/profile')
@login_required
def profile():
    user_id = session.get('user_id')
    try:
        resp = requests.get(f"{PROFILE_URL}/{user_id}", timeout=5)
        return render_template('profile.html', user=resp.json())
    except: return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id: requests.post(LOGOUT_URL, json={"user_id": user_id})
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
