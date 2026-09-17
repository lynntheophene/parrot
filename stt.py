import numpy as np
from moonshine_voice import MicTranscriber


class MoonshineSTT:
    def __init__(self):
        print("Loading Moonshine...")

        self.mic = (
            MicTranscriber()
            .language("en")
        )

        self.mic.load()

        # Reuse the loaded model.
        # Do NOT start the streaming microphone.
        self.transcriber = self.mic.transcriber

        print("Moonshine loaded.")

    def transcribe(self, audio):
        """
        Transcribe one complete utterance independently.
        """

        audio = np.asarray(audio, dtype=np.float32)

        result = self.transcriber.transcribe_without_streaming(
            audio.tolist(),
            sample_rate=16000,
        )

        if result is None:
            return ""

        # Transcript contains transcription lines.
        if hasattr(result, "lines"):
            texts = []

            for line in result.lines:
                if hasattr(line, "text"):
                    texts.append(line.text)

            return " ".join(texts).strip()

        if hasattr(result, "text"):
            return result.text.strip()

        return str(result).strip()

    def close(self):
        self.transcriber.close()