import cv2
import numpy as np
import uuid
from detector import detect_persons
from embedder import get_embedding
from milvus_client import is_new_person, store_embedding
from messaging import get_channel, send_alert_snapshot
from utils import can_alert

channel, queue = get_channel()


def callback(ch, method, properties, body):
    # try:
    frame = cv2.imdecode(np.frombuffer(body, np.uint8), cv2.IMREAD_COLOR)
    for (x1, y1, x2, y2) in detect_persons(frame):
        crop = frame[y1:y2, x1:x2]
        embedding = get_embedding(crop)
        is_new, person_id = is_new_person(embedding)

        if is_new:
            person_id = str(uuid.uuid4())
            store_embedding(embedding, person_id)

            if can_alert(person_id):
                send_alert_snapshot(frame, person_id)
                print(f"[INFO] Alert sent for {person_id}")
        else:
            print(f"[DEBUG] Skipped alert (cooldown) for {person_id}")
    # except Exception as e:
    #     print(f"[ERROR] Frame processing failed: {e}")
    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_consume(queue=queue, on_message_callback=callback)
print("[INFO] Processor started.")
channel.start_consuming()
