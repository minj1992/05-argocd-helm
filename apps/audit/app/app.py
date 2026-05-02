import pika
import sys
import os
import time
import redis
import json
import threading
from flask import Flask

app = Flask(__name__)

@app.route('/health')
def health():
    return {"status": "ok"}

def start_health_server():
    app.run(host='0.0.0.0', port=8000)

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq-svc.enterprise-lab.svc.cluster.local')
REDIS_HOST = os.getenv('REDIS_HOST', 'redis-svc.enterprise-lab.svc.cluster.local')

# Initialize Redis for Event Storage
cache = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

def callback(ch, method, properties, body):
    event_data = {
        "routing_key": method.routing_key,
        "payload": json.loads(body.decode()),
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    print(f" [AUDIT] Logging Event: {method.routing_key}")
    
    # Push to Redis list (keep last 50 events)
    cache.lpush("enterprise_audit_log", json.dumps(event_data))
    cache.ltrim("enterprise_audit_log", 0, 49)
    
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    # Start health check server in background thread
    print(f" [DEBUG] Starting health check server on port 8000...")
    threading.Thread(target=start_health_server, daemon=True).start()
    
    print(f" [DEBUG] RABBITMQ_HOST: {RABBITMQ_HOST}")
    print(f" [DEBUG] REDIS_HOST: {REDIS_HOST}")
    print(" [*] Audit Service starting... waiting for events.")
    
    # Wait for RabbitMQ to be ready
    retries = 20
    while retries > 0:
        try:
            print(f" [DEBUG] Attempting to connect to RabbitMQ at {RABBITMQ_HOST}...")
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, connection_attempts=3, retry_delay=5))
            print(" [DEBUG] RabbitMQ connected successfully!")
            break
        except Exception as e:
            print(f" [!] RabbitMQ connection failed: {e}. Retrying in 5s... ({retries} left)")
            time.sleep(5)
            retries -= 1
    else:
        print(" [!] Could not connect to RabbitMQ after 20 attempts. Exiting.")
        sys.exit(1)

    try:
        channel = connection.channel()
        print(" [DEBUG] Channel opened.")
        channel.exchange_declare(exchange='enterprise_events', exchange_type='topic')
        print(" [DEBUG] Exchange 'enterprise_events' declared.")

        result = channel.queue_declare(queue='audit_queue', durable=True)
        queue_name = result.method.queue
        print(f" [DEBUG] Queue '{queue_name}' declared.")

        # Bind to all user events
        channel.queue_bind(exchange='enterprise_events', queue=queue_name, routing_key='user.#')
        print(" [DEBUG] Queue bound to exchange.")

        channel.basic_consume(queue=queue_name, on_message_callback=callback)

        print(' [*] Waiting for logs. To exit press CTRL+C')
        channel.start_consuming()
    except Exception as e:
        print(f" [CRITICAL] Runtime error in main: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
