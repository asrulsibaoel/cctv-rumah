# Publisher: reads RTSP stream, encodes frames, and sends to LavinMQ

import cv2
import pika
import time
import os

# === CONFIG ===
RTSP_URL = os.getenv(
    "RTSP_URL", "rtsp://user:pass@camera-ip/Streaming/Channels/101")
LAVINMQ_URL = os.getenv("LAVINMQ_URL", "amqp://guest:guest@your-lavinmq-host/")
FRAME_EXCHANGE = os.getenv("FRAME_EXCHANGE", "cctv_frames")
FRAME_INTERVAL = int(os.getenv("FRAME_INTERVAL", 5))  # Send every 5 frames

# === LavinMQ Publisher Setup ===
params = pika.URLParameters(LAVINMQ_URL)
connection = pika.BlockingConnection(params)
channel = connection.channel()
channel.exchange_declare(exchange=FRAME_EXCHANGE,
                         exchange_type='fanout',
                         durable=True,
                         passive=False)

# === Capture RTSP Stream ===
print(f"Streaming to: {RTSP_URL}")


def get_capture(rtsp_url):
    for _ in range(5):
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if cap.isOpened():
            return cap
        print("[WARN] Could not open stream. Retrying in 2 seconds...")
        time.sleep(2)
    raise RuntimeError(
        "Failed to connect to RTSP stream after multiple attempts.")


cap = get_capture(RTSP_URL)

print("[INFO] Streaming and publishing frames to LavinMQ...")
frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("[WARN] Frame grab failed. Reconnecting...")
        # time.sleep(2)
        cap.release()
        cap = get_capture(RTSP_URL)
        continue

    frame_count += 1
    if frame_count % FRAME_INTERVAL != 0:
        continue

    # Resize to save bandwidth (optional)
    resized = cv2.resize(frame, (640, 360))

    # Encode as JPEG
    _, jpeg = cv2.imencode(".jpg", resized)
    channel.basic_publish(exchange=FRAME_EXCHANGE,
                          routing_key='', body=jpeg.tobytes())

    print(f"[SENT] Frame published at {time.strftime('%H:%M:%S')}")
    time.sleep(0.1)  # Optional throttle
