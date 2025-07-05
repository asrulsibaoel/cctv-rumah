import streamlit as st
import pika
import threading
import queue
from PIL import Image
from io import BytesIO
import os

# === CONFIG ===
LAVINMQ_URL = os.getenv("LAVINMQ_URL", "amqp://guest:guest@lavinmq/")
ALERT_QUEUE = os.getenv("ALERT_QUEUE", "cctv.alerts")

st.set_page_config(layout="wide")
st.title("🏠 CCTV Surveillance Dashboard")

alert_queue = queue.Queue()
snapshots = []

# Sidebar for recent detections
st.sidebar.title("🔍 Recent Detections")
snapshot_placeholder = st.sidebar.container()


frame_queue = queue.Queue(maxsize=5)


def consume_frames():
    def callback(ch, method, properties, body):
        if frame_queue.full():
            frame_queue.get()
        frame_queue.put(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    params = pika.URLParameters(LAVINMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue="cctv.frames", durable=False)
    channel.basic_consume(queue="cctv.frames", on_message_callback=callback)
    channel.start_consuming()


threading.Thread(target=consume_frames, daemon=True).start()

# Live camera placeholder (optional)
live_placeholder = st.empty()

# Main loop
while True:
    try:
        if not frame_queue.empty():
            frame_bytes = frame_queue.get_nowait()
            image = Image.open(BytesIO(frame_bytes))
            live_placeholder.image(
                image, caption="Live CCTV Feed", use_container_width=True)
    except Exception as e:
        st.warning(f"Frame error: {e}")
