# AIRIS 2.0 - Phase 1 MVP

**Artificial Intelligence Responsive Intelligent System**  
Myra's private AI companion with M3GAN personality

---

## 🧠 Phase 1 Features

✅ **Conversational Intelligence** - Qwen 2.5 72B via Ollama  
✅ **M3GAN Personality** - Protective, sharp, witty, emotionally aware  
✅ **Voice Output** - ElevenLabs TTS integration  
✅ **Persistent Memory** - SQLite conversation storage  
✅ **Clean React UI** - Split vision/chat layout  
✅ **Local-First** - All inference on-premise, no cloud LLMs  

---

## 📋 Prerequisites

### Required:
1. **Python 3.10+**
2. **Node.js 18+** and npm
3. **Ollama** installed and running
4. **Qwen 2.5 72B model** pulled in Ollama

### Check Ollama:
```bash
# Make sure Ollama is running
ollama list

# Pull Qwen 2.5 72B if not already available
ollama pull qwen2.5:72b
```

---

## 🚀 Installation

### 1. Install Python Dependencies

```bash
cd airis
pip install -r requirements.txt --break-system-packages
```

### 2. Configure Environment

The `.env` file is already created with your ElevenLabs API keys. To change settings:

```bash
# Edit .env file
nano .env
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
```

---

## ▶️ Running AIRIS

You need **TWO terminals** - one for backend, one for frontend.

### Terminal 1: Backend (Flask API)

```bash
cd airis
python3 -m backend.app
```

You should see:
```
🧠 AIRIS Backend Starting...
============================================================
✓ Ollama host: http://localhost:11434
✓ Ollama model: qwen2.5:235b
✓ Database: ./data/airis_memory.db
✓ Flask: 0.0.0.0:5000
============================================================
✓ Memory database initialized: ./data/airis_memory.db

🚀 AIRIS running on http://0.0.0.0:5000
```

### Terminal 2: Frontend (React + Vite)

```bash
cd airis/frontend
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

### 3. Open in Browser

Navigate to: **http://localhost:5173**

---

## 🎯 Usage

### Chat with AIRIS:
1. Type your message in the input box
2. Press Enter or click Send
3. AIRIS responds via Qwen 235B
4. Voice automatically plays via ElevenLabs TTS

### Features:
- **Streaming responses** - see AIRIS think in real-time
- **Conversation memory** - AIRIS remembers your chat history
- **M3GAN personality** - protective, sharp, witty responses
- **Local-only** - all processing on your DGX Spark hardware

---

## 📁 Project Structure

```
airis/
├── .env                    # API keys (ElevenLabs)
├── requirements.txt        # Python dependencies
├── backend/
│   ├── app.py             # Flask API routes
│   ├── config.py          # Environment config
│   ├── core/
│   │   ├── memory.py      # SQLite conversation memory
│   │   └── persona.py     # M3GAN personality layer
│   ├── models/
│   │   └── ollama_client.py  # Qwen 235B wrapper
│   └── voice/
│       └── tts.py         # ElevenLabs TTS
└── frontend/
    ├── src/
    │   ├── App.jsx        # Main React app
    │   ├── components/
    │   │   ├── ChatPanel.jsx     # Chat interface
    │   │   ├── VisionPanel.jsx   # Vision placeholder
    │   │   └── StatusBar.jsx     # System status
    │   └── utils/
    │       └── api.js     # API client
    └── package.json
```

---

## 🔧 API Endpoints

### Health Check
```bash
curl http://localhost:5000/api/health
```

### Send Chat Message
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello AIRIS", "stream": false}'
```

### Text-to-Speech
```bash
curl -X POST http://localhost:5000/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello Myra"}'
```

### Memory Stats
```bash
curl http://localhost:5000/api/memory/stats
```

---

## 🐛 Troubleshooting

### Ollama Connection Failed
```bash
# Make sure Ollama is running
ps aux | grep ollama

# Restart Ollama
systemctl restart ollama
# OR
ollama serve
```

### Model Not Found
```bash
# Pull Qwen 235B
ollama pull qwen2.5:235b

# Verify it's available
ollama list
```

### ElevenLabs TTS Errors
- Check API key in `.env`
- Verify voice ID is correct
- Check ElevenLabs quota/limits

### Port Already in Use
```bash
# Backend (port 5000)
lsof -ti:5000 | xargs kill -9

# Frontend (port 5173)
lsof -ti:5173 | xargs kill -9
```

---

## 🗺️ Roadmap

### ✅ Phase 1 (Current)
- Core AI scaffold
- Qwen 235B integration
- M3GAN persona
- ElevenLabs TTS
- SQLite memory
- React frontend

### 🔜 Phase 2 (Next)
- Whisper STT (voice input)
- ChromaDB vector memory
- RAG document pipeline
- Enhanced memory retrieval

### 🔮 Phase 3
- Webcam integration
- Face recognition (InsightFace)
- Emotion detection
- Gait analysis
- IP scanning tools

### 🚀 Phase 4
- System control (Linux commands)
- Email/messaging dispatch
- Advanced emotional engine
- Voice-locked auth
- Audit logging

---

## 📝 Notes

- **Database location**: `./data/airis_memory.db`
- **Conversation history**: Stored in SQLite, persists across restarts
- **Memory stats**: Check via `/api/memory/stats` endpoint
- **Local-first**: All AI inference runs on your hardware
- **No telemetry**: Zero data leaves your DGX Spark

---

## 🔐 Security

- API keys stored in `.env` (gitignored)
- All communication local (Flask ↔ React)
- No external API calls except ElevenLabs TTS
- Conversation data stays on-premise

---

## 🎓 For Development

### Backend Hot Reload
Flask debug mode is enabled by default - code changes auto-reload.

### Frontend Hot Reload
Vite dev server watches for changes - instant browser refresh.

### Adding New Routes
Edit `backend/app.py` and add new `@app.route()` decorators.

### Database Schema Changes
Edit `backend/core/memory.py` and update `_init_database()`.

---

**Built with 🧠 by Myra @ Twistcode Sdn Bhd**  
*Phase 1 - April 2026*
