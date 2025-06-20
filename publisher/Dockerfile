FROM python:3.11-slim

WORKDIR /app

COPY main.py .

RUN pip install --no-cache-dir \
    opencv-python-headless \
    pika \
    python-dotenv

CMD ["python", "main.py"]
