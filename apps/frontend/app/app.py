from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, Response
import requests
import os
import redis
import mysql.connector
import json
import markdown
from functools import wraps
from kubernetes import client, config
import base64

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
UPDATE_ROLE_URL = os.getenv('UPDATE_ROLE_URL', 'http://profile-service-svc/admin/update-role')
FORGOT_PASSWORD_URL = os.getenv('FORGOT_PASSWORD_URL', 'http://forgot-password-service-svc/reset-password')
CHANGE_PASSWORD_URL = os.getenv('CHANGE_PASSWORD_URL', 'http://login-service-svc/change-password')
LOGOUT_URL = os.getenv('LOGOUT_URL', 'http://logout-service-svc/logout')

# K8s Client Init
try:
    config.load_incluster_config()
    k8s_v1 = client.CoreV1Api()
except:
    k8s_v1 = None

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

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            resp = requests.post(REGISTER_URL, json={"username": username, "email": email, "password": password}, timeout=5)
            if resp.status_code == 201:
                flash('Registration successful! Please login.')
                return redirect(url_for('login'))
            flash('Registration failed.')
        except:
            flash('Register Service Offline')
    return render_template('register.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        try:
            resp = requests.post(FORGOT_PASSWORD_URL, json={"email": email, "new_password": new_password}, timeout=5)
            if resp.status_code == 200:
                flash('Password reset successful! Please login.')
                return redirect(url_for('login'))
            flash('User not found.')
        except:
            flash('Forgot Password Service Offline')
    return render_template('reset_password.html')

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    user_id = session.get('user_id')
    try:
        resp = requests.post(CHANGE_PASSWORD_URL, json={
            "user_id": user_id, 
            "old_password": old_password, 
            "new_password": new_password
        }, timeout=5)
        if resp.status_code == 200:
            flash('Password updated successfully!')
        else:
            flash(resp.json().get('error', 'Update failed'))
    except:
        flash('Login Service Offline')
    return redirect(url_for('profile'))

@app.route('/admin/set-role/<int:user_id>/<role>')
@login_required
@admin_required
def set_role(user_id, role):
    permissions = "Admin" if role == 'admin' else "View"
    try:
        resp = requests.post(UPDATE_ROLE_URL, json={
            "user_id": user_id, 
            "role": role, 
            "permissions": permissions
        }, timeout=5)
        if resp.status_code == 200:
            flash(f'User role updated to {role}')
        else:
            flash('Failed to update role')
    except:
        flash('Profile Service Offline')
    return redirect(url_for('manage_users'))

@app.route('/admin/download-kubeconfig')
@login_required
@admin_required
def download_kubeconfig():
    # This generates a generic kubeconfig for the current cluster
    # In a real lab, you'd use the actual cluster API server address
    api_server = f"https://{request.host.split(':')[0]}:6443"
    kubeconfig = f"""
apiVersion: v1
clusters:
- cluster:
    server: {api_server}
    skip-tls-verify: true
  name: enterprise-cluster
contexts:
- context:
    cluster: enterprise-cluster
    user: admin-user
    namespace: enterprise-lab
  name: default
current-context: default
kind: Config
preferences: {{}}
users:
- name: admin-user
  user:
    token: admin-token-placeholder
"""
    return Response(
        kubeconfig,
        mimetype="text/yaml",
        headers={"Content-disposition": "attachment; filename=kubeconfig.yaml"}
    )

@app.route('/api/cluster-info')
@login_required
def cluster_info():
    if not k8s_v1:
        return jsonify({"error": "K8s API not available"}), 500
    
    try:
        pods = k8s_v1.list_namespaced_pod("enterprise-lab")
        nodes = k8s_v1.list_node()
        namespaces = k8s_v1.list_namespace()
        
        return jsonify({
            "pods_count": len(pods.items),
            "nodes_count": len(nodes.items),
            "namespaces": [ns.metadata.name for ns in namespaces.items],
            "pods": [{"name": p.metadata.name, "status": p.status.phase} for p in pods.items]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    # Get all logs from Redis list
    logs = r.lrange("enterprise_audit_log", 0, -1)
    
    # Format logs for better readability in the text file
    formatted_logs = []
    for log_str in logs:
        try:
            log = json.loads(log_str)
            formatted_logs.append(f"[{log.get('timestamp')}] {log.get('routing_key')}: {json.dumps(log.get('payload'))}")
        except:
            formatted_logs.append(log_str)

    content = "\n".join(formatted_logs)
    if not content:
        content = "No logs found in system."
        
    return Response(
        content, 
        mimetype="text/plain", 
        headers={"Content-disposition": "attachment; filename=enterprise_audit_logs.txt"}
    )

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
