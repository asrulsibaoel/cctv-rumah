# Entry point: run on VPS or Kaggle (with internet, GPU optional)

import cv2
import base64
import time
import pika
import numpy as np
import requests
from deepface import DeepFace
from pymilvus import connections, Collection, utility, FieldSchema, CollectionSchema, DataType
from io import BytesIO
from datetime import datetime
from PIL import Image
import telegram
import torch
import torchvision.transforms as T
from torchvision.models import resnet18

# === CONFIG ===
LAVINMQ_URL = 'amqp://guest:guest@your-lavinmq-host/'
QUEUE_NAME = 'cctv.frames'
TELEGRAM_BOT_TOKEN = 'your_bot_token'
TELEGRAM_CHAT_ID = 'your_chat_id'
MILVUS_HOST = 'your-milvus-host'
COLLECTION_NAME = 'person_embeddings'
DISTANCE_THRESHOLD = 0.3  # tweak as needed

# === Torch Person Embedding Model ===
appearance_model = resnet18(pretrained=True)
appearance_model.fc = torch.nn.Identity()
appearance_model.eval()
appearance_transform = T.Compose([
    T.ToPILImage(),
    T.Resize((256, 128)),
    T.ToTensor(),
    T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# === Connect to Milvus ===
connections.connect(host=MILVUS_HOST)
if not utility.has_collection(COLLECTION_NAME):
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64,
                    is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=512),
    ]
    schema = CollectionSchema(fields, description="Person Embeddings")
    collection = Collection(COLLECTION_NAME, schema)
else:
    collection = Collection(COLLECTION_NAME)

# === Connect to Telegram ===
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)


def send_telegram_alert(image: np.ndarray, label: str):
    im = Image.fromarray(image)
    bio = BytesIO()
    im.save(bio, format="JPEG")
    bio.seek(0)
    caption = f"ALERT: {label} detected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=bio, caption=caption)


def get_person_embedding(image: np.ndarray) -> list:
    tensor = appearance_transform(image).unsqueeze(0)  # (1, 3, H, W)
    with torch.no_grad():
        embedding = appearance_model(tensor).squeeze(0).numpy()
    return embedding.tolist()


def is_new_person(embedding: list) -> bool:
    if collection.num_entities == 0:
        return True
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
    collection.load()
    results = collection.search(
        data=[embedding], anns_field="embedding", param=search_params, limit=1, output_fields=[]
    )
    if results[0][0].distance > DISTANCE_THRESHOLD:
        return True
    return False


def store_embedding(embedding: list):
    collection.insert([[embedding]])
    collection.flush()


def process_frame(frame_bytes: bytes):
    nparr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    try:
        face_objs = DeepFace.extract_faces(
            frame, detector_backend="opencv", enforce_detection=False)
        for face_obj in face_objs:
            x, y, w, h = face_obj['facial_area'].values()
            # Use this as a proxy for person crop
            cropped = frame[y:y+h, x:x+w]
            if cropped.size == 0:
                continue
            embedding = get_person_embedding(cropped)
            if is_new_person(embedding):
                send_telegram_alert(cropped, "New Person (Clothing Based)")
                store_embedding(embedding)
    except Exception as e:
        print("DeepFace/Appearance error:", e)


# === LavinMQ Consumer ===
def callback(ch, method, properties, body):
    print(f"[INFO] Frame received at {datetime.now().strftime('%H:%M:%S')}")
    process_frame(body)
    ch.basic_ack(delivery_tag=method.delivery_tag)


params = pika.URLParameters(LAVINMQ_URL)
connection = pika.BlockingConnection(params)
channel = connection.channel()
channel.queue_declare(queue=QUEUE_NAME)
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

print("[INFO] Waiting for frames...")
channel.start_consuming()
