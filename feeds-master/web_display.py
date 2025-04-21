from flask import Flask, render_template, jsonify
import os
import threading
import time
import json
from datetime import datetime

app = Flask(__name__)

# This will store our transcriptions
transcriptions = []
max_transcriptions = 100  # Maximum number of transcriptions to keep

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/transcriptions')
def get_transcriptions():
    return jsonify(transcriptions)

def add_transcription(text, timestamp=None):
    """Add a new transcription to the list"""
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    transcriptions.insert(0, {
        'text': text,
        'timestamp': timestamp,
        'keywords': []  # You could add detected keywords here
    })
    
    # Keep only the most recent entries
    while len(transcriptions) > max_transcriptions:
        transcriptions.pop()

if __name__ == '__main__':
    app.run(debug=True, port=5000)