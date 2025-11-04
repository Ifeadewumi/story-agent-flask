import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any

load_dotenv()

# ---- Flask Setup ----
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ---- Models (ported from blog) ----
class MessagePart(BaseModel):
    kind: Literal["text", "data", "file"]
    text: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    file_url: Optional[str] = None

class A2AMessage(BaseModel):
    kind: Literal["message"] = "message"
    role: Literal["user", "agent", "system"]
    parts: List[MessagePart]
    messageId: str = Field(default_factory=lambda: str(uuid4()))
    taskId: Optional[str] = None

class TaskStatus(BaseModel):
    state: Literal["working", "completed", "input-required", "failed"]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    message: Optional[A2AMessage] = None

class Artifact(BaseModel):
    artifactId: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    parts: List[MessagePart]

class TaskResult(BaseModel):
    id: str
    contextId: str
    status: TaskStatus
    artifacts: List[Artifact] = []
    history: List[A2AMessage] = []
    kind: Literal["task"] = "task"

# ---- Groq Client ----
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---- Metadata ----
AGENT_METADATA = {
    "name": "Story Agent",
    "description": "Takes in a phrase and returns a short (less than 250-word) story.",
    "version": "1.0.0",
    "author": "Ifeoluwa Adewumi",
    "framework": "Flask",
    "provider": "Groq",
    "a2a": {"endpoints": [{"name": "Story Generator", "path": "/a2a/story-agent", "method": "POST"}]},
    "health_url": "/health",
    "repo": "https://github.com/ifeadewumi/story-agent-flask",
    "logo_url": "https://i.ibb.co/Jc0Hkqs/story-logo.png"
}

@app.route("/", methods=["GET"])
def metadata():
    return jsonify(AGENT_METADATA)

@app.route("/a2a/story-agent", methods=["POST"])
def story_agent():
    body = request.get_json(force=True)

    if body.get("jsonrpc") != "2.0" or "id" not in body:
        return jsonify({
            "jsonrpc": "2.0", "id": body.get("id"),
            "error": {"code": -32600, "message": "Invalid Request"}
        }), 400

    rpc_id = body["id"]
    method = body.get("method")
    params = body.get("params", {})

    # Extract text input
    parts = []
    if method == "message/send":
        message = params.get("message", {})
        parts = message.get("parts", [])
    elif method == "execute":
        messages = params.get("messages", [])
        parts = messages[-1].get("parts", []) if messages else []
    else:
        return jsonify({
            "jsonrpc": "2.0", "id": rpc_id,
            "error": {"code": -32601, "message": "Unsupported method"}
        }), 400

    text_input = next((p.get("text") for p in parts if p.get("kind") == "text"), "")
    if not text_input:
        return jsonify({
            "jsonrpc": "2.0", "id": rpc_id,
            "error": {"code": -32602, "message": "Missing text input"}
        }), 400

    # --- Generate Story ---
    prompt = f"Write a short story (under 250 words) based on: '{text_input}'"
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )
    story = response.choices[0].message.content.strip()

    # --- Build Proper A2A Result ---
    response_msg = A2AMessage(
        role="agent",
        parts=[MessagePart(kind="text", text=story)]
    )
    result = TaskResult(
        id=str(uuid4()),
        contextId=str(uuid4()),
        status=TaskStatus(state="completed", message=response_msg),
        artifacts=[],
        history=[],
    )

    return jsonify({
        "jsonrpc": "2.0",
        "id": rpc_id,
        "result": result.model_dump()
    }), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "agent": "story-agent"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
