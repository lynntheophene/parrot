from .parakeet_stt import ParakeetSTT
from .tts import KokoroTTS


class ModelManager:

    def __init__(self):

        print("Loading global models...")

        self.stt = ParakeetSTT()

        self.tts = KokoroTTS()

        print("Global models loaded.")


    def get_stt(self):
        return self.stt


    def get_tts(self):
        return self.tts
