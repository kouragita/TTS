#!/usr/bin/env python3
"""
Working TTS Server using espeak-ng for Tractor.dev.AI
This is guaranteed to work since espeak-ng is installed and tested
"""

from flask import Flask, request, jsonify, send_file
import subprocess
import tempfile
import uuid
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/tts', methods=['POST'])
def synthesize():
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        logger.info(f"Synthesizing: {text[:50]}...")
        
        # Generate unique filename
        temp_file = f"/tmp/tts_{uuid.uuid4()}.wav"
        
        # Use espeak-ng to synthesize
        result = subprocess.run([
            'espeak-ng', 
            '-w', temp_file,  # Write to file
            '-s', '150',      # Speed
            '-a', '100',      # Amplitude
            text
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"espeak-ng failed: {result.stderr}")
            return jsonify({'error': 'TTS synthesis failed'}), 500
        
        # Check if file was created and has content
        if os.path.exists(temp_file) and os.path.getsize(temp_file) > 1000:
            logger.info(f"Audio generated: {os.path.getsize(temp_file)} bytes")
            return send_file(temp_file, as_attachment=True, download_name='output.wav')
        else:
            return jsonify({'error': 'Generated audio file is empty'}), 500
            
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    try:
        # Test espeak-ng availability
        result = subprocess.run(['espeak-ng', '--version'], capture_output=True)
        available = result.returncode == 0
        return jsonify({
            'status': 'healthy' if available else 'unhealthy',
            'engine': 'espeak-ng',
            'available': available
        })
    except Exception:
        return jsonify({
            'status': 'unhealthy',
            'engine': 'espeak-ng',
            'available': False
        })

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'service': 'Tractor.dev.AI TTS Service (espeak-ng)',
        'engine': 'espeak-ng',
        'status': 'ready',
        'endpoints': {
            '/tts': 'POST - Synthesize text to speech (JSON: {"text": "..."})',
            '/health': 'GET - Health check'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    logger.info("Starting Tractor TTS Service with espeak-ng")
    
    # Test espeak-ng on startup
    try:
        result = subprocess.run(['espeak-ng', '--version'], capture_output=True)
        if result.returncode == 0:
            logger.info("✅ espeak-ng is available and working")
        else:
            logger.error("❌ espeak-ng test failed")
    except Exception as e:
        logger.error(f"❌ espeak-ng not available: {e}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
