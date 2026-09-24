import subprocess
import tempfile
import os
import threading


class PiperTTS:

    def __init__(self):

        self.piper = os.path.expanduser(
            "~/piper/piper/piper"
        )

        self.voice = os.path.expanduser(
            "~/piper/en_US-lessac-high.onnx"
        )

        self.process = None

        self.lock = threading.Lock()

        print("Piper TTS ready.")


    def generate(self, text):

        if not text.strip():
            return b""

        wav_file = None

        try:

            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False
            ) as f:

                wav_file = f.name


            with self.lock:

                self.process = subprocess.Popen(
                    [
                        self.piper,
                        "--model",
                        self.voice,
                        "--output_file",
                        wav_file,
                    ],

                    stdin=subprocess.PIPE,

                    stdout=subprocess.DEVNULL,

                    stderr=subprocess.DEVNULL,
                )


            self.process.communicate(
                input=text.encode("utf-8")
            )


            with self.lock:
                self.process = None


            if not os.path.exists(wav_file):
                return b""


            with open(wav_file, "rb") as f:
                return f.read()


        except Exception as e:

            print(
                f"Piper TTS error: {e}"
            )

            return b""


        finally:

            with self.lock:
                self.process = None


            if (
                wav_file
                and os.path.exists(wav_file)
            ):

                try:
                    os.remove(wav_file)

                except Exception:
                    pass


    def stop(self):

        with self.lock:

            if self.process is not None:

                print(
                    "🛑 Stopping Piper"
                )

                try:

                    self.process.kill()

                except Exception:
                    pass

                self.process = None


    def close(self):

        self.stop()