from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

# Debug: Check if environment variables are loaded
print("=== Environment Variables ===")
print(f"API Key exists: {os.getenv('OPENAI_API_KEY') is not None}")
print(f"API Base: {os.getenv('OPENAI_API_BASE')}")
print(f"API Model: {os.getenv('OPENAI_API_MODEL')}")
print("============================")

app = Flask(__name__)
CORS(app)  # Allow requests from VSCode extension

# Get API credentials
api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Check your .env file!")

if not api_base:
    raise ValueError("OPENAI_API_BASE not found in environment variables. Check your .env file!")

# Initialize OpenAI client with VT-Arc settings
client = OpenAI(
    api_key=api_key,
    base_url=api_base
)

MODEL = os.getenv("OPENAI_API_MODEL", "gpt-oss-120b")
TEMPERATURE = 0.7
SYSTEM_PROMPT = "You are a helpful coding assistant. Return code in the exact format requested."

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        messages = data.get('messages', [])
        
        # Add system prompt
        full_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages
        ]
        
        print(f"Sending request to VT-Arc with {len(messages)} messages...")
        
        # Call VT-Arc API
        response = client.chat.completions.create(
            model=MODEL,
            messages=full_messages,
            temperature=TEMPERATURE
        )
        
        bot_reply = response.choices[0].message.content
        
        return jsonify({
            "success": True,
            "reply": bot_reply
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    print("Starting Python backend on http://localhost:8000")
    print(f"API Base: {os.getenv('OPENAI_API_BASE')}")
    print(f"Model: {MODEL}")
    app.run(host='0.0.0.0', port=8000, debug=True)