import os
import io
import wave
import threading

import numpy as np
from kokoro import KPipeline


class KokoroTTS:

    def __init__(self):

        print("Loading Kokoro...")

        self.kokoro = KPipeline(
            lang_code="a",
            repo_id="hexgrad/Kokoro-82M",
            device="cuda"
        )

        # One lock for the shared model.
        # Only one Kokoro inference runs at a time.
        self.lock = threading.Lock()

        print("Kokoro TTS ready.")

    def generate(self, text, stop_event):

        if not text or not text.strip():
            return b""

        # Don't start TTS if this user's request
        # has already been interrupted.
        if stop_event.is_set():
            print("🎙 Kokoro generation skipped — interrupted.")
            return b""

        try:

            # Shared model -> protected by global lock.
            with self.lock:

                # Check again after waiting for the lock.
                if stop_event.is_set():
                    print(
                        "🎙 Kokoro generation cancelled before inference."
                    )
                    return b""

                print(f"🎙 Kokoro: {text}")

                result = next(
                    self.kokoro(
                        text,
                        voice="af_sky",
                        speed=1.0
                    )
                )

            samples = result.audio
            sample_rate = 24000

            # The inference itself cannot currently be
            # force-killed, but we can discard its result
            # if THIS user's request was interrupted.
            if stop_event.is_set():
                print(
                    "🎙 Kokoro result discarded — interrupted."
                )
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

            # Final check for THIS user.
            if stop_event.is_set():
                print(
                    "🎙 Kokoro WAV discarded — interrupted."
                )
                return b""

            return wav_buffer.getvalue()

        except Exception as e:

            print(
                f"Kokoro TTS error: {e}"
            )

            return b""

    def close(self):
        """
        The Kokoro model is global/shared.

        Do NOT unload it when a user disconnects.
        """
        pass