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
    """Dynamically adjusts personality based on the selected mode."""
    
    mode_instructions = {
        "funny": "Use chaotic, viral meme energy. Use 'bro', 'nah', 'it's over'.",
        "dark": "Use dry, cynical, slightly nihilistic humor. Dark academia vibe.",
        "calm": "Be peaceful, mindful, and grounded. Soft overthinking.",
        "insanity": "GO FULL CHAOS. Use CAPS. Hyper-exaggerated drama. MEME MADNESS."
    }

    instruction = mode_instructions.get(mode, mode_instructions["funny"])

    return f"""
    Thought: "{thought}"
    Mode: {mode.upper()}
    
    Personality: {instruction}
    
    Task: Generate exactly 5 overthinking steps.
    - Max 6 words per step.
    - 1 emoji per step.
    
    Return ONLY valid JSON:
    {{
      "steps": ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
      "mood": "{mode}"
    }}
    """

def parse_ai_response(text, thought, mode="funny"):
    # ... (existing robust parsing logic)
    """Extracts JSON from the AI response with multiple fallback layers to ensure stability."""
    # Debug: Print raw response to console
    logger.info(f"--- RAW AI RESPONSE ---\n{text}\n-----------------------")

    # The 'Safe Fallback' so the frontend never crashes
    fallback_data = {
        "steps": [
            f"Hmm, why am I worried about '{thought}'? 🤔",
            "What if this is the start of a trend? 📉",
            "I should probably check my emails again... 😬",
            "Maybe I'll just stay in bed forever. 🏠",
            "Wait, I was overthinking that, wasn't I? 😅"
        ],
        "mood": "neutral"
    }

    try:
        # Layer 1: Direct JSON extraction
        # We look for the first '{' and the last '}'
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            clean_json = match.group()
            data = json.loads(clean_json)
            
            # Validation: Ensure it has steps and mood
            if "steps" in data and isinstance(data["steps"], list) and len(data["steps"]) >= 3:
                # Ensure we have exactly 5 steps (pad or trim)
                steps = data["steps"][:5]
                while len(steps) < 5:
                    steps.append("...and then the brain gave up. 😵")
                data["steps"] = steps
                data["mood"] = data.get("mood", "neutral")
                return data

        # Layer 2: Plain text split (if AI returns lines instead of JSON)
        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 5]
        if len(lines) >= 3:
            logger.warning("AI failed JSON format, but returned lines. Converting to JSON.")
            return {
                "steps": lines[:5],
                "mood": "neutral"
            }

    except Exception as e:
        logger.error(f"Critcal parsing error: {e}")

    # Layer 3: Return the fallback if all else fails
    logger.warning("Using hardcoded fallback response.")
    return fallback_data

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

if __name__ == "__main__":
    app.run(debug=True, port=5000)