import cv2
import torch
import numpy as np
from PIL import Image
from torchreid import models
from torchreid.data.transforms import build_transforms

device = torch.device("cpu")
transform_train, transform_test = build_transforms(
    height=256, width=128, is_train=False)
transform = transform_test

model = models.build_model(
    name="osnet_x1_0", num_classes=1000, pretrained=True)
model.to(device)
model.eval()


def get_embedding(bgr_image: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    tensor = transform(pil_img).unsqueeze(0).to(device)
    with torch.no_grad():
        features = model(tensor).cpu().numpy()[0]
    norm = np.linalg.norm(features)
    return features / norm if norm > 0 else features
