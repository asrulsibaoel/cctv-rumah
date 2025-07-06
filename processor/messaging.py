import pika
import json
import base64
import cv2
from datetime import datetime
from settings import LAVINMQ_URL, FRAME_EXCHANGE, ALERT_EXCHANGE

params = pika.URLParameters(LAVINMQ_URL)
connection = pika.BlockingConnection(params)
channel = connection.channel()

channel.exchange_declare(exchange=FRAME_EXCHANGE,
                         exchange_type='fanout',
                         durable=True,
                         passive=False)
channel.exchange_declare(exchange=ALERT_EXCHANGE,
                         exchange_type='fanout',
                         durable=True,
                         passive=False)

result = channel.queue_declare(queue='', exclusive=True)
frame_queue = result.method.queue
channel.queue_bind(exchange=FRAME_EXCHANGE, queue=frame_queue)


def get_channel():
    return channel, frame_queue


def send_alert_snapshot(frame, person_id: str):
    _, buffer = cv2.imencode(".jpg", frame)
    encoded = base64.b64encode(buffer).decode("utf-8")
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "person_id": person_id,
        "image": encoded
    }
    channel.basic_publish(exchange=ALERT_EXCHANGE,
                          routing_key='', body=json.dumps(payload))
