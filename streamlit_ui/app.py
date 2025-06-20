# streamlit_ui/app.py

import streamlit as st
import pika
import threading
import queue
from PIL import Image
from io import BytesIO
import time

# === CONFIG ===
LAVINMQ_URL = st.secrets.get("LAVINMQ_URL", "amqp://guest:guest@lavinmq/")
QUEUE_NAME = st.secrets.get("QUEUE_NAME", "cctv.frames")

st.set_page_config(layout="wide")
st.title("🏠 CCTV Surveillance Dashboard")

frame_queue = queue.Queue(maxsize=10)
snapshots = []  # To store recent snapshots (images)

live_placeholder = st.empty()
snapshot_container = st.container()


def consume_frames():
    def callback(ch, method, properties, body):
        if frame_queue.full():
            try:
                frame_queue.get_nowait()
            except queue.Empty:
                pass
        frame_queue.put(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    params = pika.URLParameters(LAVINMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
    channel.start_consuming()


# Start consumer thread
threading.Thread(target=consume_frames, daemon=True).start()

while True:
    try:
        frame_bytes = frame_queue.get(timeout=5)
        image = Image.open(BytesIO(frame_bytes))
        live_placeholder.image(
            image, caption="Live CCTV Feed", use_column_width=True)

        # Save snapshot (keep last 5)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        snapshots.append((timestamp, image.copy()))
        if len(snapshots) > 5:
            snapshots.pop(0)

        # Display snapshots in columns
        with snapshot_container:
            st.subheader("🔍 Recent Detections")
            cols = st.columns(5)
            for idx, (ts, snap) in enumerate(snapshots):
                with cols[idx]:
                    st.image(snap, caption=ts, use_column_width=True)

    except queue.Empty:
        st.warning("Waiting for new frames...")
        time.sleep(1)
    except Exception as e:
        st.error(f"Error displaying frames: {e}")
        time.sleep(2)
