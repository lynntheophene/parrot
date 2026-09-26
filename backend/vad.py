import torch
from silero_vad import load_silero_vad
import threading

class SileroVAD:

    def __init__(self):

        self.speaking = False
        self.paplay_process = None
        self.lock = threading.Lock()

        print("Loading Silero VAD...")

        self.model = load_silero_vad()

        print("Silero VAD loaded.")

    def speech_probability(self, audio):

        # Make sure audio is float32
        audio = audio.astype("float32")

        # Convert NumPy → PyTorch
        audio_tensor = torch.from_numpy(audio)

        # Ask Silero whether this chunk contains speech
        speech_probability = self.model(audio_tensor,16000).item()

        return speech_probability

    def is_speech(self,audio):
        probability = self.speech_probability(audio)
        return probability > 0.6
