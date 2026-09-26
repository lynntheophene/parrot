import time
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

        self.transcriber = self.mic.transcriber

        print("Moonshine loaded.")

    def transcribe(self, audio):

        total_start = time.perf_counter()

        # Convert audio
        convert_start = time.perf_counter()

        audio = np.asarray(
            audio,
            dtype=np.float32
        )

        convert_time = (
            time.perf_counter() - convert_start
        )

        print(
            f"⏱ STT audio conversion: "
            f"{convert_time:.3f}s"
        )

        print(
            f"🎧 STT audio length: "
            f"{len(audio) / 16000:.2f}s"
        )

        # Moonshine inference
        inference_start = time.perf_counter()

        result = self.transcriber.transcribe_without_streaming(
            audio.tolist(),
            sample_rate=16000,
        )

        inference_time = (
            time.perf_counter() - inference_start
        )

        print(
            f"⏱ Moonshine inference: "
            f"{inference_time:.3f}s"
        )

        if result is None:
            return ""

        if hasattr(result, "lines"):

            texts = []

            for line in result.lines:

                if hasattr(line, "text"):
                    texts.append(line.text)

            text = " ".join(texts).strip()

        elif hasattr(result, "text"):

            text = result.text.strip()

        else:

            text = str(result).strip()

        total_time = (
            time.perf_counter() - total_start
        )

        print(
            f"⏱ Total STT processing: "
            f"{total_time:.3f}s"
        )

        return text

    def close(self):
        self.transcriber.close()