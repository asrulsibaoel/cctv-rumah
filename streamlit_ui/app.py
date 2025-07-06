import streamlit as st
import pika
import threading
import queue
from PIL import Image
from io import BytesIO
import os
import json
import base64
import time

# === CONFIG ===
LAVINMQ_URL = os.getenv("LAVINMQ_URL", "amqp://guest:guest@lavinmq/")
FRAME_EXCHANGE = os.getenv("FRAME_EXCHANGE", "cctv_frames")
ALERT_EXCHANGE = os.getenv("ALERT_EXCHANGE", "cctv_alerts")
ALERT_COOLDOWN = int(os.getenv("ALERT_COOLDOWN", 10))  # seconds
FRAME_UPDATE_INTERVAL = 0.1  # seconds

# === UI SETUP ===
st.set_page_config(layout="wide")
st.title("🏠 CCTV Surveillance Dashboard")

# Sidebar for recent detections
st.sidebar.title("🔍 Recent Detections")
snapshot_placeholder = st.sidebar.container()
live_placeholder = st.empty()

# === Thread-safe queues ===
frame_queue = queue.Queue(maxsize=5)
alert_queue = queue.Queue(maxsize=10)

# === Track recent alerts to avoid spamming ===
if "recent_detections" not in st.session_state:
    st.session_state.recent_detections = []

if "last_alert_times" not in st.session_state:
    st.session_state.last_alert_times = {}

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

# === Helper: Process Alerts with Cooldown ===


def process_alert(alert):
    person_id = alert.get("person_id", "unknown")
    timestamp = alert.get("timestamp", "Unknown")
    b64_image = alert.get("image")

    now = time.time()
    last_alert = st.session_state.last_alert_times.get(person_id)

    if last_alert and now - last_alert < ALERT_COOLDOWN:
        return  # Cooldown not expired

    st.session_state.last_alert_times[person_id] = now

    if b64_image:
        img_bytes = base64.b64decode(b64_image)
        st.session_state.recent_detections.insert(0, {
            "timestamp": timestamp,
            "image": img_bytes
        })
        st.session_state.recent_detections = st.session_state.recent_detections[:5]


# === Start Consumers in Background Threads ===
threading.Thread(target=consume_frames, daemon=True).start()
threading.Thread(target=consume_alerts, daemon=True).start()

# === MAIN UI LOOP ===
while True:
    try:
        # Show Live Frame
        if not frame_queue.empty():
            frame_bytes = frame_queue.get_nowait()
            image = Image.open(BytesIO(frame_bytes))
            live_placeholder.image(
                image, caption="Live CCTV Feed", use_container_width=True)

        # Handle Alerts
        while not alert_queue.empty():
            alert = alert_queue.get_nowait()
            process_alert(alert)

        # Render Sidebar
        with snapshot_placeholder:
            for detection in st.session_state.recent_detections:
                st.image(
                    detection["image"], caption=f"⏱️ {detection['timestamp']}", use_container_width=True)

        time.sleep(FRAME_UPDATE_INTERVAL)

    except Exception as e:
        st.warning(f"Stream error: {e}")
        time.sleep(1)
