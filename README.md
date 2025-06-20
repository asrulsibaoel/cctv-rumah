# CCTV Surveillance System with DeepFace, LavinMQ, Milvus & Telegram Alerts

This system captures real-time CCTV frames, analyzes for new persons using DeepFace and clothing similarity, stores embeddings in Milvus, and sends Telegram alerts. A Streamlit dashboard displays live stream and snapshots.

---

## 🧱 Architecture Overview

* **Camera**: RTSP/ONVIF CCTV camera
* **Publisher**: Sends frames to LavinMQ queue
* **Processor**: Detects faces + appearance, compares with Milvus, alerts via Telegram
* **Streamlit UI**: Live video + recent detection snapshots
* **Milvus**: Vector store for embeddings
* **LavinMQ**: Message broker for streaming frames

---

## 📁 Folder Structure

```bash
cctv-surveillance-system/
├── docker-compose.yml
├── .env.example
├── README.md
├── publisher/
│   ├── Dockerfile
│   └── main.py
├── processor/
│   ├── Dockerfile
│   └── main.py
├── streamlit_ui/
│   ├── Dockerfile
│   └── app.py
```

---

## ⚙️ Environment Configuration

Create a `.env` file based on this template:

```env
# .env.example
RTSP_URL=rtsp://user:pass@192.168.1.2:554/Streaming/Channels/101
LAVINMQ_URL=amqp://guest:guest@lavinmq/
QUEUE_NAME=cctv.frames
TELEGRAM_BOT_TOKEN=123456:ABC-def...
TELEGRAM_CHAT_ID=123456789
MILVUS_HOST=milvus
COLLECTION_NAME=person_embeddings
```

---

## 🚀 Running the System

1. **Clone the repo**

```bash
git clone https://github.com/your-org/cctv-surveillance-system.git
cd cctv-surveillance-system
```

2. **Add your `.env` file** to the root directory.

3. **Build & Run** using Docker Compose:

```bash
docker-compose up --build
```

4. **Access the UI**:

* Streamlit dashboard: [http://localhost:8501](http://localhost:8501)
* LavinMQ UI: [http://localhost:15672](http://localhost:15672) (guest/guest)

---

## ✅ Features

* Detect new faces and clothing (appearance)
* Store and compare embeddings in Milvus
* Publish frames from RTSP camera
* Real-time notifications via Telegram bot
* Live Streamlit dashboard with snapshot history

---

## 🔐 Security Tips

* Use strong passwords for LavinMQ and camera stream
* Set Streamlit behind authentication or VPN
* Limit public access to ports in production

---

## 📦 Requirements (for local development)

Each sub-folder can optionally include a `requirements.txt`, for example:

**publisher/requirements.txt**

```
pika
opencv-python-headless
python-dotenv
```

**processor/requirements.txt**

```
pika
deepface
torch
torchvision
pymilvus
python-telegram-bot
opencv-python-headless
```

**streamlit\_ui/requirements.txt**

```
streamlit
pika
pillow
numpy
```

---

## 🧠 Future Extensions

* Multi-camera support
* Face re-identification via clustering
* Integration with object detection (e.g. YOLOv8)
* Auto-purging old embeddings in Milvus

---

## 🛠 Authors

* Maintainer: [Asrul Sani Ariesandy](https://github.com/asrulsibaoel)
* Powered by: Python, LavinMQ, Milvus, DeepFace, Streamlit, Docker

---

## 📄 License

MIT or custom license of your choice
