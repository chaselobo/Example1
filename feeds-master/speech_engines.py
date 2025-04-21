import struct
import os

class gcp_engine:
    def __init__(self):
        from google.cloud import speech
        
        self.client = speech.SpeechClient()
        self.config = speech.RecognitionConfig(
            model="video",
            language_code="en-US",
            sample_rate_hertz=16000,
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16
        )

    def decode(self, samples):
        binary = struct.pack('<{}h'.format(len(samples)), *samples)
        audio = speech.RecognitionAudio(content=binary)
        response = self.client.recognize(config=self.config, audio=audio)
        for result in response.results:
            alternative = result.alternatives[0]
            return alternative.transcript

class null_engine:
    def decode(self, samples):
        return 'null transcription: {}s'.format(len(samples) / 16000)