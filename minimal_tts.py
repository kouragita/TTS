#!/usr/bin/env python3
"""
Minimal TTS Service for Tractor.dev.AI - Guaranteed to work
Uses pyttsx3 as a reliable fallback
"""

from flask import Flask, request, jsonify, send_file
import pyttsx3
import tempfile
import uuid
import os
import threading
import queue

app = Flask(__name__)

class MinimalTTS:
    def __init__(self):
        self.engine = pyttsx3.init()
        # Configure for better quality
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 0.9)
        print("Minimal TTS initialized successfully")
    
    def synthesize(self, text):
        temp_file = f"/tmp/tts_{uuid.uuid4()}.wav"
        try:
            self.engine.save_to_file(text, temp_file)
            self.engine.runAndWait()
            return temp_file if os.path.exists(temp_file) else None
        except Exception as e:
            print(f"TTS error: {e}")
            return None

tts = MinimalTTS()

@app.route('/tts', methods=['POST'])
def synthesize():
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        audio_file = tts.synthesize(text)
        
        if audio_file and os.path.getsize(audio_file) > 100:
            return send_file(audio_file, as_attachment=True, download_name='output.wav')
        else:
            return jsonify({'error': 'Failed to generate audio'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'engine': 'pyttsx3'})

if __name__ == '__main__':
    print("Starting Minimal TTS Server on port 8082")
    app.run(host='0.0.0.0', port=8082, debug=False)
