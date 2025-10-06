#!/usr/bin/env python3
"""
TTS Workaround v2 for PyTorch compatibility issues
This script patches the torch.load function and handles XTTS properly
"""

import torch
import sys
import os
import traceback

# Patch torch.load to use weights_only=False
original_load = torch.load

def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)

torch.load = patched_load

# Now import TTS after patching
from TTS.api import TTS
from flask import Flask, request, jsonify, send_file
import tempfile
import uuid
import numpy as np

app = Flask(__name__)

# Initialize TTS model
print("Loading TTS model...")
tts = None

try:
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
    print("XTTS v2 model loaded successfully!")
    model_type = "xtts"
except Exception as e:
    print(f"Failed to load XTTS v2: {e}")
    try:
        tts = TTS("tts_models/en/ljspeech/vits")
        print("VITS model loaded successfully!")
        model_type = "vits"
    except Exception as e2:
        print(f"Failed to load VITS model: {e2}")
        sys.exit(1)

@app.route('/tts', methods=['POST'])
def synthesize():
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        print(f"Synthesizing: {text}")
        
        # Generate audio
        temp_file = f"/tmp/tts_{uuid.uuid4()}.wav"
        
        if model_type == "xtts":
            # For XTTS, we need to provide a speaker reference
            # Use the default speaker or clone from a reference
            wav = tts.tts(text=text, language="en")
            
            # Save the audio
            import soundfile as sf
            if isinstance(wav, list):
                wav = np.array(wav)
            sf.write(temp_file, wav, 22050)
        else:
            # For VITS and other models
            tts.tts_to_file(text=text, file_path=temp_file)
        
        print(f"Audio saved to: {temp_file}")
        
        if os.path.exists(temp_file) and os.path.getsize(temp_file) > 1000:  # Check if file has content
            return send_file(temp_file, as_attachment=True, download_name='output.wav')
        else:
            return jsonify({'error': 'Generated audio file is empty or too small'}), 500
        
    except Exception as e:
        print(f"Error in synthesis: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy', 
        'model_type': model_type,
        'model': str(type(tts.synthesizer.tts_model)) if tts else 'None'
    })

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'service': 'TTS Workaround Server',
        'model_type': model_type,
        'endpoints': {
            '/tts': 'POST - Synthesize text to speech',
            '/health': 'GET - Health check'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8083))  # Use different port to avoid conflicts
    print(f"Starting TTS Workaround Server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
