import os
import io
import wave
import threading
os.environ["ONNX_PROVIDER"] = "CUDAExecutionProvider"
import numpy as np
from kokoro_onnx import Kokoro


class KokoroTTS:

    def __init__(self):

        self.model = os.path.expanduser(
            "~/parrot/models/kokoro/kokoro-v1.0.onnx"
        )

        self.voices = os.path.expanduser(
            "~/parrot/models/kokoro/voices-v1.0.bin"
        )

        self.lock = threading.Lock()

        # Used to invalidate TTS work when the user interrupts.
        self.stop_event = threading.Event()

        print("Loading Kokoro...")

        self.kokoro = Kokoro(
            self.model,
            self.voices,
        )

        print("Kokoro TTS ready.")

    def generate(self, text):

        if not text or not text.strip():
            return b""

        # Don't start new TTS work after interruption.
        if self.stop_event.is_set():
            print("🎙 Kokoro generation skipped — interrupted.")
            return b""

        try:

            with self.lock:

                # Check again after acquiring the lock.
                if self.stop_event.is_set():
                    print("🎙 Kokoro generation cancelled before inference.")
                    return b""

                print(f"🎙 Kokoro: {text}")

                samples, sample_rate = self.kokoro.create(
                    text,
                    voice="af_sky",
                    speed=1.0,
                    lang="en-us",
                )

            # Inference itself cannot currently be force-killed,
            # but its result can be discarded immediately.
            if self.stop_event.is_set():
                print("🎙 Kokoro result discarded — interrupted.")
                return b""

            if samples is None:
                return b""

            samples = np.asarray(
                samples,
                dtype=np.float32
            )

            samples = np.clip(
                samples,
                -1.0,
                1.0
            )

            pcm = (
                samples * 32767
            ).astype(
                np.int16
            )

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

            # Final cancellation check before returning audio.
            if self.stop_event.is_set():
                print("🎙 Kokoro WAV discarded — interrupted.")
                return b""

            return wav_buffer.getvalue()

        except Exception as e:

            print(
                f"Kokoro TTS error: {e}"
            )

            return b""

    def stop(self):

        print("Kokoro stop requested.")

        # Invalidate the currently running generation.
        self.stop_event.set()

    def reset(self):

        # Allow the next response to generate TTS again.
        self.stop_event.clear()

    def close(self):

        self.stop()


    