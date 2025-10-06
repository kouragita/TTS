#!/usr/bin/env python3
"""
Simple TTS Server using pyttsx3 as a fallback for Coqui TTS issues
"""

from flask import Flask, request, jsonify, send_file
import pyttsx3
import tempfile
import uuid
import os
import threading
import queue

app = Flask(__name__)

class TTSEngine:
    def __init__(self):
        self.engine = None
        self.init_engine()
    
    def init_engine(self):
        try:
            self.engine = pyttsx3.init()
            # Set properties for better quality
            voices = self.engine.getProperty('voices')
            if voices:
                # Try to find a female voice or use the first available
                for voice in voices:
                    if 'female' in voice.name.lower() or 'woman' in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
                else:
                    self.engine.setProperty('voice', voices[0].id)
            
            # Set speech rate and volume
            self.engine.setProperty('rate', 150)  # Speed of speech
            self.engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
            print("TTS Engine initialized successfully")
        except Exception as e:
            print(f"Failed to initialize TTS engine: {e}")
            self.engine = None
    
    def synthesize(self, text, output_file):
        if not self.engine:
            raise Exception("TTS engine not initialized")
        
        try:
            # Use a queue to handle the async nature of pyttsx3
            result_queue = queue.Queue()
            
            def on_word(name, location, length):
                pass
            
            def on_end(name, completed):
                result_queue.put(True)
            
            self.engine.connect('started-word', on_word)
            self.engine.connect('finished-utterance', on_end)
            
            # Save to file
            self.engine.save_to_file(text, output_file)
            self.engine.runAndWait()
            
            return True
        except Exception as e:
            print(f"TTS synthesis error: {e}")
            return False

# Initialize TTS engine
tts_engine = TTSEngine()

@app.route('/tts', methods=['POST'])
def synthesize():
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Generate unique filename
        temp_file = f"/tmp/tts_{uuid.uuid4()}.wav"
        
        # Synthesize speech
        success = tts_engine.synthesize(text, temp_file)
        
        if success and os.path.exists(temp_file):
            return send_file(temp_file, as_attachment=True, download_name='output.wav')
        else:
            return jsonify({'error': 'Failed to generate speech'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy', 
        'engine': 'pyttsx3',
        'available': tts_engine.engine is not None
    })

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'service': 'Simple TTS Server',
        'endpoints': {
            '/tts': 'POST - Synthesize text to speech',
            '/health': 'GET - Health check'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    print(f"Starting Simple TTS Server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
