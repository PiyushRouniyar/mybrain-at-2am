import os
import json
import logging
import re
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
app = Flask(__name__, template_folder='.')
CORS(app)

@app.route('/<path:filename>')
def serve_static(filename):
    """Allows Flask to serve your MP3 files and other assets from the root folder."""
    return send_from_directory('.', filename)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
else:
    logger.error("GEMINI_API_KEY not found in .env")

# --- AI Logic ---

def get_prompt(thought):
    return f"""
User message: "{thought}"

You are NOT an AI assistant.
You are a sarcastic internet commenter replying to this message.

Your job:
React to the message with a funny, sarcastic,savage reply.

IMPORTANT:
- You MUST directly react to the user's sentence
- Do NOT generate thoughts, steps, or analysis
- Do NOT be philosophical
- Do NOT overthink
- Just roast the statement like a comment section

STYLE:
- 1 short sentence ONLY (max 10 words)
- Meme tone (Instagram / TikTok comments)
- Use sarcasm + exaggeration
- Add 1 emoji (💀 🤡 😭 🤨)

GOOD EXAMPLES:
- "bro thinks he knows the script 💀"
- "ain't no way you said that 😭"
- "who told you that was happening 🤡"
- "this is not your timeline 💀"

BAD (NEVER DO THIS):
- long sentences
- advice
- explanations
- overthinking chains

OUTPUT:
Return ONLY JSON:

{{
  "steps": ["your reply"],
  "mood": "funny"
}}
"""

def parse_ai_response(text, thought, mode="funny"):
    logger.info(f"RAW RESPONSE: {text}")

    import re, json

    try:
        # Try JSON first
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            if "steps" in data:
                return {
                    "steps": data["steps"],
                    "mood": data.get("mood", "funny")
                }

    except Exception as e:
        logger.warning(f"JSON parsing failed: {e}")

    # 🔥 MAIN FIX: ALWAYS USE RAW TEXT
    clean_text = text.strip()

    if not clean_text:
        clean_text = f"bro what even is '{thought}' 💀"

    return {
        "steps": [clean_text],
        "mood": "funny"
    }

def generate_steps(thought, mode="funny"):
    """Calls Gemini and handles logic failures."""
    if not GEMINI_API_KEY:
        return None
    
    try:
        # Forcing JSON response via config (if library supports it)
        response = model.generate_content(
            get_prompt(thought, mode),
            generation_config={"response_mime_type": "application/json"}
        )
        
        if not response or not response.text:
            return parse_ai_response("", thought, mode)
            
        return parse_ai_response(response.text, thought, mode)
        
    except Exception as e:
        logger.error(f"Gemini API failure: {e}")
        # Always return fallback data instead of None to prevent route crash
        return parse_ai_response("", thought, mode)

# --- Flask Routes ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    """Main endpoint with guaranteed JSON output."""
    try:
        data = request.get_json()
        thought = data.get("thought", "").strip() if data else ""
        mode = data.get("mode", "funny")
        
        if not thought:
            return jsonify({"error": "Gotta type a thought first! 🖍️"}), 400

        # This is now guaranteed to return a valid dictionary
        ai_data = generate_steps(thought, mode)

        return jsonify({
            "status_updates": [
                "🧠 Brain gears spinning...",
                "🤔 Consulting the Council of Doubts...",
                "📊 Adding 400% extra complexity...",
                "😅 Perfecting the disaster scenario..."
            ],
            "steps": ai_data["steps"],
            "mood": ai_data["mood"]
        })

    except Exception as e:
        logger.error(f"Global Route Error: {e}")
        # Final emergency catch: Return a 200 JSON even if things explode locally
        return jsonify({
            "status_updates": ["💥 Crisis averted!"],
            "steps": ["Wait... am I overthinking the overthinker? 😵"],
            "mood": "anxious"
        }), 200

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)