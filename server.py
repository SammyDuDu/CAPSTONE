import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS

# Initialize the Flask application
app = Flask(__name__)

# IMPORTANT: Enable CORS (Cross-Origin Resource Sharing)
# This allows your frontend (hosted on GitHub Pages, a different domain) to make requests to this backend.
# In a production environment, you would restrict origins to your specific GitHub Pages URL.
CORS(app)

@app.route('/api/analyze-vowel', methods=['POST'])
def analyze_vowel():
    """
    Handles the audio file upload, simulates acoustic analysis, and returns a score.
    """
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']
    
    # Optional: You can access other form data like the target vowel
    target_vowel = request.form.get('target', 'unknown')
    
    # CRITICAL: If you were using real analysis, this is where you would:
    # 1. Save the file temporarily: audio_file.save('/tmp/input.webm')
    # 2. Use Librosa/SciPy to load and process the audio (e.g., extract formants).
    # 3. Compare formants to target_vowel data to calculate a real score.
    
    # --- MOCK ANALYSIS ---
    # Since we don't have the heavy acoustic libraries installed here, 
    # we simulate a 1-second delay and generate a random score (50-99).
    import time
    time.sleep(1) 
    
    simulated_score = random.randint(50, 99)
    
    # Return the result in JSON format
    return jsonify({
        "score": simulated_score,
        "feedback": f"Mock analysis complete for target '{target_vowel}'.",
        "timestamp": time.time()
    }), 200

# Render typically runs on Gunicorn, but for simple local testing:
if __name__ == '__main__':
    # Use environment variable for port or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
