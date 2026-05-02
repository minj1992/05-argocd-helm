from flask import Flask, request, jsonify
import os
import redis

app = Flask(__name__)

# Config
cache = redis.Redis(host=os.getenv('REDIS_HOST', 'redis-svc'), port=6379, decode_responses=True)

from mq_helper import publish_event

@app.route('/logout', methods=['POST'])
def logout():
    data = request.json
    user_id = data.get('user_id')
    if user_id:
        cache.delete(f"session_{user_id}")
        publish_event("logout", {"user_id": user_id})
        return jsonify({"message": "Logout successful"})
    return jsonify({"error": "User ID required"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
