import pika
import json
import os

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq-svc')

def publish_event(event_type, data):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=600, blocked_connection_timeout=300)
        )
        channel = connection.channel()
        channel.exchange_declare(exchange='enterprise_events', exchange_type='topic')
        
        routing_key = f"user.{event_type}"
        message = {
            "event": event_type,
            "data": data
        }
        
        channel.basic_publish(
            exchange='enterprise_events',
            routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2) # Persistent
        )
        connection.close()
        print(f" [x] Sent {routing_key}")
    except Exception as e:
        print(f" [!] Failed to publish event: {e}")
