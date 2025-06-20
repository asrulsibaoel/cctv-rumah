# Publisher: reads RTSP stream, encodes frames, and sends to LavinMQ

import cv2
import pika
import time
import os
import base64

# === CONFIG ===
RTSP_URL = os.getenv(
    "RTSP_URL", "rtsp://user:pass@camera-ip/Streaming/Channels/101")
LAVINMQ_URL = os.getenv("LAVINMQ_URL", "amqp://guest:guest@your-lavinmq-host/")
QUEUE_NAME = os.getenv("QUEUE_NAME", "cctv.frames")
FRAME_INTERVAL = int(os.getenv("FRAME_INTERVAL", 5))  # Send every 5 frames

# === LavinMQ Publisher Setup ===
params = pika.URLParameters(LAVINMQ_URL)
connection = pika.BlockingConnection(params)
channel = connection.channel()
channel.queue_declare(queue=QUEUE_NAME, durable=True)

# === Capture RTSP Stream ===
cap = cv2.VideoCapture(RTSP_URL)
if not cap.isOpened():
    raise Exception(f"Failed to connect to RTSP stream: {RTSP_URL}")

print("[INFO] Streaming and publishing frames to LavinMQ...")
frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("[WARN] Frame grab failed. Reconnecting...")
        time.sleep(2)
        cap.release()
        cap = cv2.VideoCapture(RTSP_URL)
        continue

    frame_count += 1
    if frame_count % FRAME_INTERVAL != 0:
        continue

    # Resize to save bandwidth (optional)
    resized = cv2.resize(frame, (640, 360))

    # Encode as JPEG
    _, jpeg = cv2.imencode(".jpg", resized)
    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=jpeg.tobytes(),
        properties=pika.BasicProperties(
            delivery_mode=2)  # Make message persistent
    )

    print(f"[SENT] Frame published at {time.strftime('%H:%M:%S')}")
    time.sleep(0.1)  # Optional throttle
