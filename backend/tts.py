import os
import io
import wave
import threading

import numpy as np
from kokoro_onnx import Kokoro


class KokoroTTS:

    def __init__(self):

        self.model = os.path.expanduser(
            "~/voice-agent/models/kokoro-v1.0.onnx"
        )

        self.voices = os.path.expanduser(
            "~/voice-agent/models/voices-v1.0.bin"
        )

        self.lock = threading.Lock()

        print("Loading Kokoro...")

        self.kokoro = Kokoro(
            self.model,
            self.voices
        )

        print("Kokoro TTS ready.")


    def generate(self, text):

        if not text or not text.strip():
            return b""

        try:

            with self.lock:

                print(f"🎙 Kokoro: {text}")

                samples, sample_rate = self.kokoro.create(
                    text,
                    voice="af_sky",
                    speed=1.0,
                    lang="en-us",
                )

            if samples is None:
                return b""

            # Convert to numpy
            samples = np.asarray(
                samples,
                dtype=np.float32
            )

            # Prevent clipping
            samples = np.clip(
                samples,
                -1.0,
                1.0
            )

            # Float32 → PCM16
            pcm = (
                samples * 32767
            ).astype(
                np.int16
            )

            # Create WAV in memory
            wav_buffer = io.BytesIO()

            with wave.open(
                wav_buffer,
                "wb"
            ) as wav:

                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)

                wav.writeframes(
                    pcm.tobytes()
                )

            return wav_buffer.getvalue()


        except Exception as e:

            print(
                f"Kokoro TTS error: {e}"
            )

            return b""


    def stop(self):

        # Kokoro runs inside the Python process,
        # so there is no subprocess to kill.

        print("Kokoro stop requested.")


    def close(self):

        self.stop()