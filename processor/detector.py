from typing import List, Tuple
from ultralytics import YOLO

yolo_model = YOLO("yolov8n.pt")


def detect_persons(frame) -> List[Tuple[int, int, int, int]]:
    results = yolo_model.predict(source=frame, classes=[
                                 0], conf=0.4, verbose=False)
    boxes = []
    for r in results:
        if r.boxes is not None:
            for box in r.boxes.xyxy.cpu().numpy():
                x1, y1, x2, y2 = map(int, box)
                boxes.append((x1, y1, x2, y2))
    return boxes
