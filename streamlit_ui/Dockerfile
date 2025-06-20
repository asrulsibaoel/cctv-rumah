FROM python:3.11-slim

WORKDIR /app

COPY app.py .

RUN pip install --no-cache-dir \
    streamlit \
    pika \
    numpy \
    pillow

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
