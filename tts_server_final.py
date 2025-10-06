#!/usr/bin/env python3
"""
Final TTS Server Solution for Tractor.dev.AI
Handles PyTorch compatibility and XTTS speaker requirements
"""

import torch
import sys
import os
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Patch torch.load to use weights_only=False for compatibility
original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)
torch.load = patched_load

from flask import Flask, request, jsonify, send_file
import tempfile
import uuid
import numpy as np

app = Flask(__name__)

class TTSService:
    def __init__(self):
        self.tts = None
        self.model_type = None
        self.default_speaker = None
        self.reference_audio = None
        self.initialize_tts()
    
    def initialize_tts(self):
        """Initialize TTS with fallback options"""
        logger.info("Initializing TTS service...")
        
        # Try XTTS v2 first
        try:
            from TTS.api import TTS
            self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            self.model_type = "xtts"
            logger.info("XTTS v2 loaded successfully!")
            
            # Set up reference audio for voice cloning
            ref_path = "/home/kouragita/tractor-dev-ai/tts_coqui/habari.wav"
            if os.path.exists(ref_path):
                self.reference_audio = ref_path
                logger.info(f"Using reference audio: {ref_path}")
            else:
                logger.warning("No reference audio found, will try without")
                
        except Exception as e:
            logger.error(f"XTTS v2 failed: {e}")
            
            # Fallback to simpler model
            try:
                from TTS.api import TTS
                self.tts = TTS("tts_models/en/ljspeech/vits")
                self.model_type = "vits"
                logger.info("VITS model loaded as fallback")
            except Exception as e2:
                logger.error(f"VITS fallback failed: {e2}")
                
                # Final fallback to pyttsx3
                try:
                    import pyttsx3
                    self.tts = pyttsx3.init()
                    self.model_type = "pyttsx3"
                    logger.info("Using pyttsx3 as final fallback")
                except Exception as e3:
                    logger.error(f"All TTS options failed: {e3}")
                    self.tts = None
    
    def synthesize(self, text, language="en"):
        """Synthesize speech from text"""
        if not self.tts:
            raise Exception("No TTS engine available")
        
        temp_file = f"/tmp/tts_{uuid.uuid4()}.wav"
        
        try:
            if self.model_type == "xtts":
                # Handle XTTS with proper speaker reference
                if self.reference_audio:
                    wav = self.tts.tts(text=text, speaker_wav=self.reference_audio, language=language)
                else:
                    # Try without speaker reference (might work for some versions)
                    wav = self.tts.tts(text=text, language=language)
                
                # Save audio
                import soundfile as sf
                if isinstance(wav, list):
                    wav = np.array(wav)
                sf.write(temp_file, wav, 22050)
                
            elif self.model_type == "vits":
                self.tts.tts_to_file(text=text, file_path=temp_file)
                
            elif self.model_type == "pyttsx3":
                self.tts.save_to_file(text, temp_file)
                self.tts.runAndWait()
            
            return temp_file if os.path.exists(temp_file) and os.path.getsize(temp_file) > 100 else None
            
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return None

# Initialize TTS service
tts_service = TTSService()

@app.route('/tts', methods=['POST'])
def synthesize():
    try:
        data = request.get_json()
        text = data.get('text', '')
        language = data.get('language', 'en')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        logger.info(f"Synthesizing: {text[:50]}...")
        
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
        'status': 'healthy' if tts_service.tts else 'unhealthy',
        'model_type': tts_service.model_type,
        'reference_audio': tts_service.reference_audio is not None
    })

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'service': 'Tractor.dev.AI TTS Server',
        'model_type': tts_service.model_type,
        'status': 'ready' if tts_service.tts else 'failed'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    logger.info(f"Starting Tractor TTS Server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
