# Story Agent

### Description
The Story Agent takes in a simple phrase and returns a short (less than 250-word) creative story using Groq’s LLaMA 3.1 model.

---

## Features
- Phrase-to-story generation in seconds
- JSON-based A2A interface (Telex-compatible)
- Built with Python + Flask
- Logging + health checks included

---

##  API Endpoints

### `GET /`
Returns agent metadata for Telex registration.

### `GET /health`
Health check route — returns `{ "status": "ok" }`.

### `POST /a2a/story-agent`
Accepts Telex payload:
```json
{
  "event": "message_created",
  "message": { "text": "A lonely robot dreams of the ocean" }
}```

Responds with:

```json
{
  "data": {
    "response_type": "in_channel",
    "text": "Once, in a scrapyard beyond the dunes..."
  }
}```

---

## Setup Instructions

```bash
git clone https://github.com/Ifeadewumi/story-agent-flask.git
cd story-agent
pip install -r requirements.txt
echo "GROQ_API_KEY=your_key_here" > .env
python app.py
```

The app will start on http://localhost:3000

## Deployment
Deploy easily via Railway or Render.

Ensure your environment variables include:

```bash
GROQ_API_KEY=your_api_key
PORT=3000
```
