import streamlit as st
import pika
import threading
import queue
from PIL import Image
from io import BytesIO
import os
import json
import base64
from datetime import datetime, timedelta
import time

# === CONFIG ===
LAVINMQ_URL = os.getenv("LAVINMQ_URL", "amqp://guest:guest@lavinmq/")
FRAME_EXCHANGE = os.getenv("FRAME_EXCHANGE", "cctv_frames")
ALERT_EXCHANGE = os.getenv("ALERT_EXCHANGE", "cctv_alerts")
ALERT_EXPIRY_SECONDS = 60

# === UI SETUP ===
st.set_page_config(layout="wide")
st.title("🏠 CCTV Surveillance Dashboard")

# Sidebar for recent detections
st.sidebar.title("🔍 Recent Unique Persons")
snapshot_placeholder = st.sidebar.container()

frame_queue = queue.Queue(maxsize=5)
alert_queue = queue.Queue(maxsize=10)

# === THREAD: LIVE FRAME CONSUMER ===


def consume_frames():
    def callback(ch, method, properties, body):
        if frame_queue.full():
            frame_queue.get()
        frame_queue.put(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    params = pika.URLParameters(LAVINMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.exchange_declare(
        exchange=FRAME_EXCHANGE, exchange_type='fanout', durable=True, passive=False)
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange=FRAME_EXCHANGE, queue=queue_name)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)
    channel.start_consuming()

# === THREAD: ALERT SNAPSHOT CONSUMER ===


def consume_alerts():
    def callback(ch, method, properties, body):
        try:
            alert = json.loads(body.decode())
            if alert_queue.full():
                alert_queue.get()
            alert_queue.put(alert)
        except Exception as e:
            print(f"[WARN] Error parsing alert: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    params = pika.URLParameters(LAVINMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.exchange_declare(
        exchange=ALERT_EXCHANGE, exchange_type='fanout', durable=True, passive=False)
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange=ALERT_EXCHANGE, queue=queue_name)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)
    channel.start_consuming()


# Start background threads
threading.Thread(target=consume_frames, daemon=True).start()
threading.Thread(target=consume_alerts, daemon=True).start()

# === MAIN LOOP ===
live_placeholder = st.empty()
recent_alerts = {}  # person_id -> {"image": ..., "timestamp": datetime}

while True:
    frame_updated = False
    alert_updated = False

    try:
        # === Handle frame stream ===
        if not frame_queue.empty():
            frame_bytes = frame_queue.get_nowait()
            image = Image.open(BytesIO(frame_bytes))
            live_placeholder.image(
                image, caption="📺 Live CCTV Feed", use_container_width=True)
            frame_updated = True

        # === Handle new alerts ===
        if not alert_queue.empty():
            alert = alert_queue.get_nowait()
            person_id = alert.get("person_id")
            b64_image = alert.get("image")
            ts_str = alert.get("timestamp")

            if person_id and b64_image and ts_str:
                try:
                    img_bytes = base64.b64decode(b64_image)
                    timestamp = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    recent_alerts[person_id] = {
                        "image": img_bytes,
                        "timestamp": timestamp,
                    }
                    alert_updated = True
                except Exception as e:
                    print(f"[WARN] Failed to decode alert: {e}")

        # === Clean expired alerts ===
        now = datetime.now()
        expired_keys = [pid for pid, val in recent_alerts.items()
                        if now - val["timestamp"] > timedelta(seconds=ALERT_EXPIRY_SECONDS)]
        for pid in expired_keys:
            del recent_alerts[pid]
            alert_updated = True

        # === Only update sidebar if alert updated ===
        if alert_updated:
            snapshot_placeholder.empty()  # 🧹 Clear sidebar container

            with snapshot_placeholder:
                st.subheader("🧠 Recent Unique Persons")
                if not recent_alerts:
                    st.markdown("*(No detections yet)*")
                else:
                    sorted_alerts = sorted(
                        recent_alerts.items(),
                        key=lambda x: x[1]["timestamp"],
                        reverse=True
                    )
                    for person_id, val in sorted_alerts:
                        ts_label = val["timestamp"].strftime("%H:%M:%S")
                        st.image(
                            val["image"], caption=f"{person_id} at {ts_label}", use_container_width=True)

    except Exception as e:
        st.warning(f"Stream error: {e}")

    # ⏱ Prevent CPU hogging and UI spam
    time.sleep(0.1)
