import os
import cv2
import time
import pika
import json
import base64
import numpy as np
from deepface import DeepFace

# RabbitMQ setup
LAVINMQ_URL = os.getenv("LAVINMQ_URL", "amqp://guest:guest@lavinmq/")
FRAME_QUEUE = os.getenv("FRAME_QUEUE", "cctv.frames")
ALERT_QUEUE = os.getenv("ALERT_QUEUE", "cctv.alerts")

# Load model
model = DeepFace.build_model("Facenet512")

# Connect to LavinMQ
params = pika.URLParameters(LAVINMQ_URL)
conn = pika.BlockingConnection(params)
channel = conn.channel()
channel.queue_declare(queue=FRAME_QUEUE, durable=False)

# Setup alert channel
alert_conn = pika.BlockingConnection(params)
alert_channel = alert_conn.channel()
alert_channel.queue_declare(queue=ALERT_QUEUE, durable=False)

known_embeddings = []


def send_alert_snapshot(frame):
    _, buffer = cv2.imencode(".jpg", frame)
    encoded_image = base64.b64encode(buffer).decode("utf-8")
    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "image": encoded_image
    }
    alert_channel.basic_publish(
        exchange="",
        routing_key=ALERT_QUEUE,
        body=json.dumps(payload)
    )
    print("[INFO] Sent alert snapshot to LavinMQ")


def callback(ch, method, properties, body):
    nparr = np.frombuffer(body, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    try:
        result = DeepFace.represent(
            frame, model_name="Facenet512", detector_backend="yolov8", enforce_detection=False)
        if result:
            embedding = result[0]["embedding"]
            is_new = all(np.linalg.norm(np.array(embedding) -
                         np.array(e)) > 0.6 for e in known_embeddings)
            if is_new:
                known_embeddings.append(embedding)
                send_alert_snapshot(frame)
        else:
            send_alert_snapshot

    except Exception as e:
        print(f"[ERROR] Face processing failed: {e}")

    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=FRAME_QUEUE, on_message_callback=callback)
print("[INFO] Processor started. Waiting for frames...")
channel.start_consuming()
