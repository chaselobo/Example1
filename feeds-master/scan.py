#!/usr/bin/env python3
import os
import queue
import threading
import argparse
import logging
import hashlib
import tempfile
from dotenv import load_dotenv
# Import needed components
from speech_engines import gcp_engine, null_engine
from web_display import add_transcription, app
from mic_stream import mic_thread

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import needed components from your files
from speech_engines import gcp_engine, null_engine
from audio_stream import ffmpeg_thread
from trunk_stream import BroadcastifyCallSystem, scraper_thread
from keyword_detector import detect_keywords
from twilio_sender import send_sms_alert

# Configuration - Replace with your actual values
KEYWORDS = ["party", "disturbance", "emergency", "gunshot"]
PHONE_NUMBERS = ["+1234567890", "+0987654321"]  # Replace with actual phone numbers
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "your_account_sid")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "your_auth_token")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "+1234567890")

def tts_stream(queue, engine):
    """Process audio from queue, transcribe, and return calls with text."""
    while True:
        call = queue.get()
        if call.duration < 0.750:  # Skip very short audio segments
            continue
        samples = call.audio_segment.get_array_of_samples()
        text = engine.decode(samples)
        if text:
            call.text = text
            yield call

def main():
    # Parse command line arguments
    

    parser = argparse.ArgumentParser(description="Police Radio Scanner with Keyword Alerts")
    parser.add_argument('--engine', '-e', 
                        choices=('gcp', 'none'),
                        default='gcp',
                        help='Speech recognition engine to use')
    parser.add_argument('--type',
                        choices=('mic', 'audio', 'trunk'),
                        required=True,
                        help='Stream type (audio URL or Broadcastify)')
    parser.add_argument('--record',
                        help='Path to save recordings')
    parser.add_argument('stream',
                        nargs='?',  # Make this argument optional
                        default=None,  # Set a default value if not provided
                        help='Stream URL or Broadcastify system ID')
    
    args = parser.parse_args()
    
    # Start the web server in a background thread
    flask_thread = threading.Thread(target=lambda: app.run(debug=False, port=5000, use_reloader=False))
    flask_thread.daemon = True
    flask_thread.start()
    logger.info("Web interface started at http://localhost:5000")

    # Set up speech recognition engine
    if args.engine == 'gcp':
        engine = gcp_engine()
    elif args.engine == 'none':
        engine = null_engine()
    
    # Set up audio queue and stream
    call_queue = queue.Queue()
    
    if args.type == 'trunk':
        # For Broadcastify feeds
        cookie = os.environ.get('BCFY_COOKIE')
        if not cookie:
            raise ValueError('Missing cookie for Broadcastify. Set BCFY_COOKIE environment variable.')
        
        call_system = BroadcastifyCallSystem(args.stream, cookie, hydrate=60)
        thread = threading.Thread(target=scraper_thread, args=(call_system, call_queue))
        thread.start()
        logger.info(f"Started Broadcastify feed ID: {args.stream}")
    
    elif args.type == 'mic':
    # For microphone input
        thread = threading.Thread(target=mic_thread, args=(call_queue,))
        thread.start()
        logger.info("Started microphone capture")

    elif args.type == 'audio':
        # For direct audio streams
        thread = threading.Thread(target=ffmpeg_thread, args=(args.stream, call_queue))
        thread.start()
        logger.info(f"Started audio stream: {args.stream}")
    
    # Create recording directory if specified
    if args.record:
        os.makedirs(args.record, exist_ok=True)
        logger.info(f"Saving recordings to: {args.record}")
    
    # Process transcriptions
    logger.info(f"Started processing with {args.engine} engine")
    try:
        for call in tts_stream(call_queue, engine):
            # Print the transcription
            logger.info(f"{call.ts}: {call.text}")
            
            # Print the transcription
            logger.info(f"{call.ts}: {call.text}")
            add_transcription(call.text, timestamp=call.ts.isoformat())  # Send to web display

            # Save recordings if requested
            if args.record:
                path = ''
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                    path = f.name
                    call.audio_segment.export(path, format='mp3', parameters=['-codec:a', 'libmp3lame', '-qscale:a','2'])
                with open(path, 'rb') as f:
                    data = f.read()
                    sha1 = hashlib.sha1(data).hexdigest()
                with open(os.path.join(args.record, sha1 + '.mp3'), 'wb') as f:
                    f.write(data)
                with open(os.path.join(args.record, sha1 + '.txt'), 'w') as f:
                    f.write(call.text + '\n')
                os.unlink(path)
            
            # Check for keywords
            found_keywords = detect_keywords(call.text, KEYWORDS)
            
            # Send alerts if keywords found
            if found_keywords:
                logger.info(f"Keywords detected: {found_keywords}")
                try:
                    send_sms_alert(
                        call.text,
                        found_keywords,
                        PHONE_NUMBERS,
                        TWILIO_ACCOUNT_SID,
                        TWILIO_AUTH_TOKEN,
                        TWILIO_FROM_NUMBER
                    )
                    logger.info(f"SMS alert sent to {len(PHONE_NUMBERS)} numbers")
                except Exception as e:
                    logger.error(f"Failed to send SMS: {e}")
    
    except KeyboardInterrupt:
        logger.info("Stopping scanner...")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        raise

if __name__ == "__main__":
    main()