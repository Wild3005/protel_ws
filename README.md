# Smart Vending Machine AI (PROTEL)

## 🚀 Overview
Project ini adalah sistem vending machine berbasis:
- LLM (Ollama)
- Web interface
- MQTT communication
- ESP32 (hardware)

---

## 🧠 Features
- Input natural language (LLM)
- Manual ingredient selection
- JSON-based communication
- MQTT publish ke mesin

---

## 🏗️ Architecture

User (Web)
↓
FastAPI (LLM processing)
↓
MQTT Broker
↓
ESP32 (Vending Machine)

---

## ⚙️ Requirements

- Docker & Docker Compose
- Ollama (local LLM)

Install Ollama:
https://ollama.com

---

## ▶️ Run Project

### 1. Jalankan Ollama
```bash
ollama serve