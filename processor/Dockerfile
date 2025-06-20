FROM python:3.11-slim

WORKDIR /app

COPY main.py .

RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && \
    pip install --no-cache-dir \
    deepface \
    pika \
    python-telegram-bot \
    pymilvus \
    torch torchvision torchaudio \
    opencv-python-headless \
    numpy pillow

CMD ["python", "main.py"]
