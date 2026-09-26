
import subprocess
import threading
import sounddevice as sd
import soundfile as sf
import tempfile
import os


class PiperTTS:

    def __init__(self):

        self.speaking = False
        self.stop_event = threading.Event()
        self.thread = None

        # Your actual Piper paths
        self.piper = os.path.expanduser(
            "~/piper/piper/piper"
        )

        self.voice = os.path.expanduser(
            "~/piper/en_US-lessac-high.onnx"
        )

        print("Piper TTS ready.")

    def speak(self, text):

        if not text.strip():
            return

        # Stop previous speech
        self.stop()

        # Reset stop flag
        self.stop_event.clear()

        self.thread = threading.Thread(
            target=self._speak_worker,
            args=(text,),
            daemon=True
        )

        self.thread.start()

    def _speak_worker(self, text):

        wav_file = None

        try:

            # Temporary WAV file
            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False
            ) as f:
                wav_file = f.name

            # Generate speech with Piper
            subprocess.run(
                [
                    self.piper,
                    "--model",
                    self.voice,
                    "--output_file",
                    wav_file
                ],
                input=text.encode("utf-8"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Was Piper interrupted while generating?
            if self.stop_event.is_set():
                return

            # Load generated audio
            audio, sample_rate = sf.read(
                wav_file,
                dtype="float32"
            )

            # Check again before playback
            if self.stop_event.is_set():
                return

            self.speaking = True

            # Start playback
            sd.play(audio, sample_rate)

            # Wait until playback finishes
            # or user interrupts
            while True:

                if self.stop_event.is_set():
                    sd.stop()
                    break

                if not sd.get_stream().active:
                    break

                sd.sleep(20)

        except Exception as e:

            print(f"Piper TTS error: {e}")

        finally:

            sd.stop()

            self.speaking = False

            if wav_file and os.path.exists(wav_file):

                try:
                    os.remove(wav_file)
                except Exception:
                    pass

    def stop(self):

        # Tell worker to stop
        self.stop_event.set()

        # Stop audio immediately
        sd.stop()

        self.speaking = False

    def is_speaking(self):

        return self.speaking

    def close(self):

        self.stop()

