#!/usr/bin/env python3
"""
TTS Workaround for PyTorch compatibility issues
This script patches the torch.load function to use weights_only=False
"""

import torch
import sys
import os

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

app = Flask(__name__)

# Initialize TTS model
print("Loading TTS model...")
try:
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
    print("TTS model loaded successfully!")
except Exception as e:
    print(f"Failed to load XTTS v2, trying simpler model: {e}")
    try:
        tts = TTS("tts_models/en/ljspeech/vits")
        print("Fallback TTS model loaded successfully!")
    except Exception as e2:
        print(f"Failed to load fallback model: {e2}")
        sys.exit(1)

@app.route('/tts', methods=['POST'])
def synthesize():
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Generate audio
        temp_file = f"/tmp/tts_{uuid.uuid4()}.wav"
        
        # Use different synthesis methods based on model
        if hasattr(tts, 'tts_to_file'):
            tts.tts_to_file(text=text, file_path=temp_file)
        else:
            # For XTTS models that need speaker reference
            wav = tts.tts(text=text)
            import soundfile as sf
            sf.write(temp_file, wav, 22050)
        
        return send_file(temp_file, as_attachment=True, download_name='output.wav')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'model': str(type(tts.synthesizer.tts_model))})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    app.run(host='0.0.0.0', port=port, debug=False)
