import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from groq import Groq
from utils import is_valid_telex_payload, make_a2a_response
from datetime import datetime
from uuid import uuid4


load_dotenv()

app = Flask(__name__)

# --- 🧠 Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),  # logs to a file named app.log
        logging.StreamHandler()          # also logs to the console
    ]
)

# Log every incoming request
@app.before_request
def log_request():
    app.logger.info(f"Incoming {request.method} request → {request.path}")
    if request.is_json:
        app.logger.info(f"Request body: {request.get_json()}")

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- Agent Metadata (Telex/Mastra Spec) ---
AGENT_METADATA = {
    "name": "Story Agent",
    "description": "Takes in a phrase and returns a short (less than 250-word) story.",
    "version": "1.0.0",
    "author": "Ifeoluwa Adewumi",
    "language": "Python",
    "framework": "Flask",
    "provider": "Groq",
    "a2a": {
        "endpoints": [
            {
                "name": "Story Generator",
                "path": "/a2a/story-agent",
                "description": "Generates a story based on the provided phrase",
                "method": "POST"
            }
        ]
    },
    "health_url": "/health",
    "repo": "https://github.com/ifeadewumi/story-agent-flask",
    "logo_url": "https://i.ibb.co/Jc0Hkqs/story-logo.png"
}


@app.route("/", methods=["GET"])
def metadata():
    """Return metadata required for Telex registration."""
    return jsonify(AGENT_METADATA)

@app.route("/a2a/story-agent", methods=["POST"])
def story_agent():
    """
    A2A-compliant endpoint: processes JSON-RPC requests and returns structured responses.
    """
    try:
        body = request.get_json(force=True)

        # ✅ Validate JSON-RPC structure
        if body.get("jsonrpc") != "2.0" or "id" not in body:
            return jsonify({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: jsonrpc must be '2.0' and 'id' is required."
                }
            }), 400

        rpc_id = body["id"]
        method = body.get("method")
        params = body.get("params", {})

        # Extract message text from A2A structure
        if method == "message/send":
            message = params.get("message", {})
            parts = message.get("parts", [])
        elif method == "execute":
            messages = params.get("messages", [])
            parts = messages[-1].get("parts", []) if messages else []
        else:
            return jsonify({
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32601, "message": "Unsupported method"}
            }), 400

        # Get text input
        text_input = ""
        for part in parts:
            if part.get("kind") == "text" and part.get("text"):
                text_input = part["text"].strip()
                break

        if not text_input:
            return jsonify({
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32602, "message": "Missing text input in request."}
            }), 400

        # 🧠 Generate story using Groq
        prompt = f"Write a short story (under 250 words) based on the phrase: '{text_input}'"
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
        )
        story = response.choices[0].message.content.strip()

        # ✅ Build A2A TaskResult-compliant response
        result = {
            "id": str(uuid4()),
            "contextId": str(uuid4()),
            "status": {
                "state": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "message": {
                    "kind": "message",
                    "role": "agent",
                    "parts": [{"kind": "text", "text": story}],
                },
            },
            "artifacts": [],
            "history": [],
            "kind": "task",
        }

        return jsonify({
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": result
        }), 200

    except Exception as e:
        return jsonify({
            "jsonrpc": "2.0",
            "id": body.get("id") if "body" in locals() else None,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": {"details": str(e)},
            },
        }), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "agent": "story-agent"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
