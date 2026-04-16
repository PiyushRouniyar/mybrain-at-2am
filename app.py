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

def get_prompt(thought, mode="funny"):
    # Using a more aggressive "roast" personality to override any previous habits
    return f"""
INSTRUCTIONS:
You are a savage internet commenter from 2026. 
You are replying to the user's message with peak sarcasm and brain rot energy.

USER INPUT: "{thought}"

TASK: 
Generate EXACTLY 5 unique, short, meme-style sarcastic roast replies.

STRICT REQUIREMENTS:
1. Length: Each reply must be UNDER 8 words.
2. Emoji: Include 1 emoji per reply (💀, 😭😭, 🤡, 👁️👄👁️).
3. Vibe: Instagram/TikTok comment section roasts.
4. Variety: Each of the 5 replies MUST have a different sentence structure.
5. NO Thoughts: Do not include "I am worried" or "Hmm" or any AI overthinking.

STRICT JSON OUTPUT:
{{
  "steps": [
    "ROAST 1 💀",
    "ROAST 2 😭",
    "ROAST 3 🤡",
    "ROAST 4 🤨",
    "ROAST 5 💀"
  ],
  "mood": "{mode}"
}}
"""

def parse_ai_response(text, thought, mode="funny"):
    logger.info(f"RAW AI RESPONSE: {text}")

    if not text or not text.strip():
        return {"steps": [f"bro really thought '{thought}' was worth a reply 💀"], "mood": mode}

    try:
        # 1. Try to find JSON block
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            if "steps" in data and isinstance(data["steps"], list) and len(data["steps"]) >= 1:
                return {
                    "steps": [str(s).strip() for s in data["steps"]],
                    "mood": data.get("mood", mode)
                }
    except Exception as e:
        logger.warning(f"JSON Parsing failed: {e}")

    # 2. Extract lines if JSON fail or incomplete
    # Split by newline, remove common bullet points/numbers
    lines = [
        re.sub(r'^[\-\d\.\s*]+', '', line).strip().strip('"') 
        for line in text.split('\n') 
        if line.strip() and not line.strip().startswith(('{', '}', '"'))
    ]
    
    if lines:
        return {
            "steps": lines[:10], # Cap at 10 just in case
            "mood": mode
        }

    # 3. Last fallback: return the raw text as a single reply
    return {
        "steps": [text.strip()[:100]],
        "mood": mode
    }

def generate_steps(thought, mode="funny"):
    """Calls Gemini and handles logic failures."""
    if not GEMINI_API_KEY:
        return {"steps": ["API KEY MISSING 💀"], "mood": "anxious"}
    
    try:
        prompt = get_prompt(thought, mode)
        logger.info(f"--- SENDING PROMPT ---\n{prompt}")
        
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        if not response or not response.text:
            logger.error("Gemini returned empty response")
            return parse_ai_response("", thought, mode)
            
        logger.info(f"--- RECEIVED RESPONSE ---\n{response.text}")
        return parse_ai_response(response.text, thought, mode)
        
    except Exception as e:
        logger.error(f"Gemini API failure: {e}")
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