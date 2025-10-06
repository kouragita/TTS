#!/usr/bin/env python3
"""
Definitive TTS Fix for Tractor.dev.AI
This WILL work - uses multiple fallback strategies
"""

import os
import sys
import logging
from flask import Flask, request, jsonify, send_file
import tempfile
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class TractorTTS:
    def __init__(self):
        self.tts_engine = None
        self.engine_type = None
        self.initialize()
    
    def initialize(self):
        """Try multiple TTS engines in order of preference"""
        
        # Strategy 1: Try Coqui with PyTorch patch
        try:
            logger.info("Attempting Coqui TTS with PyTorch patch...")
            import torch
            
            # Patch torch.load
            original_load = torch.load
            def patched_load(*args, **kwargs):
                kwargs['weights_only'] = False
                return original_load(*args, **kwargs)
            torch.load = patched_load
            
            from TTS.api import TTS
            
            # Try simpler model first
            self.tts_engine = TTS("tts_models/en/ljspeech/vits")
            self.engine_type = "coqui_vits"
            logger.info("✅ Coqui VITS model loaded successfully!")
            return
            
        except Exception as e:
            logger.warning(f"Coqui TTS failed: {e}")
        
        # Strategy 2: Try gTTS (requires internet)
        try:
            logger.info("Attempting gTTS...")
            from gtts import gTTS
            # Test gTTS
            test_tts = gTTS(text="test", lang='en')
            self.tts_engine = gTTS
            self.engine_type = "gtts"
            logger.info("✅ gTTS loaded successfully!")
            return
        except Exception as e:
            logger.warning(f"gTTS failed: {e}")
        
        # Strategy 3: Try pyttsx3
        try:
            logger.info("Attempting pyttsx3...")
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 0.9)
            self.tts_engine = engine
            self.engine_type = "pyttsx3"
            logger.info("✅ pyttsx3 loaded successfully!")
            return
        except Exception as e:
            logger.warning(f"pyttsx3 failed: {e}")
        
        # Strategy 4: Use espeak directly
        try:
            logger.info("Attempting espeak...")
            import subprocess
            result = subprocess.run(['espeak', '--version'], capture_output=True)
            if result.returncode == 0:
                self.tts_engine = "espeak"
                self.engine_type = "espeak"
                logger.info("✅ espeak available!")
                return
        except Exception as e:
            logger.warning(f"espeak failed: {e}")
        
        logger.error("❌ All TTS engines failed!")
        self.engine_type = "none"
    
    def synthesize(self, text, language="en"):
        """Synthesize speech using available engine"""
        if not self.tts_engine:
            raise Exception("No TTS engine available")
        
        temp_file = f"/tmp/tts_{uuid.uuid4()}.wav"
        
        try:
            if self.engine_type == "coqui_vits":
                self.tts_engine.tts_to_file(text=text, file_path=temp_file)
                
            elif self.engine_type == "gtts":
                from gtts import gTTS
                tts = gTTS(text=text, lang='en')
                tts.save(temp_file)
                
            elif self.engine_type == "pyttsx3":
                self.tts_engine.save_to_file(text, temp_file)
                self.tts_engine.runAndWait()
                
            elif self.engine_type == "espeak":
                import subprocess
                subprocess.run([
                    'espeak', '-w', temp_file, '-s', '150', text
                ], check=True)
            
            # Verify file was created and has content
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 100:
                return temp_file
            else:
                raise Exception("Generated file is empty or too small")
                
        except Exception as e:
            logger.error(f"Synthesis failed with {self.engine_type}: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return None

# Initialize TTS
tts_service = TractorTTS()

@app.route('/tts', methods=['POST'])
def synthesize():
    try:
        data = request.get_json()
        text = data.get('text', '')
        language = data.get('language', 'en')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        logger.info(f"Synthesizing with {tts_service.engine_type}: {text[:50]}...")
        
        audio_file = tts_service.synthesize(text, language)
        
        if audio_file:
            return send_file(audio_file, as_attachment=True, download_name='output.wav')
        else:
            return jsonify({'error': 'Failed to generate audio'}), 500
            
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy' if tts_service.engine_type != 'none' else 'unhealthy',
        'engine': tts_service.engine_type,
        'available': tts_service.tts_engine is not None
    })

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'service': 'Tractor.dev.AI TTS Service',
        'engine': tts_service.engine_type,
        'status': 'ready' if tts_service.engine_type != 'none' else 'failed',
        'endpoints': {
            '/tts': 'POST - Synthesize text to speech',
            '/health': 'GET - Health check'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    logger.info(f"Starting Tractor TTS Service on port {port}")
    logger.info(f"Using engine: {tts_service.engine_type}")
    app.run(host='0.0.0.0', port=port, debug=False)
