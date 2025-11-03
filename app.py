import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from groq import Groq
from utils import is_valid_telex_payload, make_a2a_response

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

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- Agent Metadata (Telex/Mastra Spec) ---
AGENT_METADATA = {
    "name": "Story Agent",
    "description": "Takes in a phrase and returns a short (less than 250-word) story.",
    "version": "1.0.0",
    "author": "Your Name",
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
    "repo": "https://github.com/yourusername/story-agent",
    "logo_url": "https://i.ibb.co/Jc0Hkqs/story-logo.png"
}


@app.route("/", methods=["GET"])
def metadata():
    """Return metadata required for Telex registration."""
    return jsonify(AGENT_METADATA)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/a2a/story-agent", methods=["POST"])
def story_agent():
    try:
        body = request.get_json(force=True)

        if not is_valid_telex_payload(body):
            return jsonify({"error": "Invalid payload"}), 400

        phrase = body["message"]["text"].strip()
        if not phrase:
            return jsonify(make_a2a_response("Please provide a phrase to base the story on!"))

        prompt = f"Write a short story (under 250 words) inspired by this phrase: '{phrase}'"

        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a creative storyteller."},
                {"role": "user", "content": prompt}
            ]
        )

        story = completion.choices[0].message.content.strip()
        return jsonify(make_a2a_response(story))

    except Exception as e:
        print("Agent error:", e)
        return jsonify({"error": "internal_error", "detail": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
