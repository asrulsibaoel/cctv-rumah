import os
from datetime import timedelta

MILVUS_URI = os.getenv("MILVUS_URI", "https://YOUR-MILVUS-URL")
MILVUS_TOKEN = os.getenv("MILVUS_TOKEN", "your-token")
MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "your-token")

LAVINMQ_URL = os.getenv("LAVINMQ_URL", "amqp://guest:guest@lavinmq/")
FRAME_EXCHANGE = os.getenv("FRAME_EXCHANGE", "cctv_frames")
ALERT_EXCHANGE = os.getenv("ALERT_EXCHANGE", "cctv_alerts")

ALERT_INTERVAL = timedelta(seconds=10)
