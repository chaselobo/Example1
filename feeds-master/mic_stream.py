import pyaudio
import wave
import array
import datetime
import queue
import threading
import time
from dataclasses import dataclass
import pydub
import webrtcvad

# Reuse the Call dataclass structure
@dataclass
class Call:
    ts: datetime.datetime
    duration: float
    audio_segment: pydub.AudioSegment
    text: str

def mic_thread(q, chunk_size=1024, format=pyaudio.paInt16, channels=1, rate=16000):
    """
    Capture audio from microphone, detect speech, and add chunks to queue.
    """
    p = pyaudio.PyAudio()
    
    # Open microphone stream
    stream = p.open(format=format,
                    channels=channels,
                    rate=rate,
                    input=True,
                    frames_per_buffer=chunk_size)
    
    print("* Listening... Press Ctrl+C to stop.")
    
    # Voice activity detection
    vad = webrtcvad.Vad(3)  # Aggressiveness level 3 (highest)
    vad_frame_size = 480  # 30ms at 16kHz
    
    # Buffer for speech chunks
    speech_buffer = []
    silent_frames = 0
    max_silent_frames = 30  # About 1 second of silence to end a speech segment
    
    try:
        while True:
            data = stream.read(vad_frame_size, exception_on_overflow=False)
            
            # Check if frame contains speech
            is_speech = vad.is_speech(data, rate)
            
            if is_speech:
                speech_buffer.append(data)
                silent_frames = 0
            else:
                silent_frames += 1
            
            # If we've collected speech and then had silence, process the segment
            if len(speech_buffer) > 0 and silent_frames >= max_silent_frames:
                raw_speech = b''.join(speech_buffer)
                
                # Convert to audio segment
                samples = array.array('h', raw_speech)
                segment = (pydub.AudioSegment.empty()
                           .set_sample_width(2)
                           .set_channels(1)
                           .set_frame_rate(rate))
                audio_segment = segment._spawn(samples)
                duration = len(samples) / rate
                
                # Create call object and add to queue
                call = Call(ts=datetime.datetime.utcnow(), 
                            audio_segment=audio_segment, 
                            duration=duration, 
                            text='')
                q.put(call)
                
                # Clear buffer for next speech segment
                speech_buffer = []
                print("* Speech segment captured, processing...")
    
    except KeyboardInterrupt:
        print("* Recording stopped")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    # Test the microphone capture
    q = queue.Queue()
    thread = threading.Thread(target=mic_thread, args=(q,))
    thread.start()
    
    try:
        while True:
            if not q.empty():
                call = q.get()
                print(f"Captured speech segment: {call.duration:.2f} seconds")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping...")