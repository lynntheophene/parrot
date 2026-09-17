import subprocess
import os
import threading
import queue


class PiperTTS:
    def __init__(self):
        self.piper = os.path.expanduser("~/piper/piper/piper")
        self.model = os.path.expanduser("~/piper/en_US-lessac-high.onnx")

        self.process = subprocess.Popen(
            [
                self.piper,
                "--model",
                self.model,
                "--output_raw",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

        self.audio_queue = queue.Queue()
        self.stop_event = threading.Event()

        self.reader_thread = threading.Thread(
            target=self._read_audio,
            daemon=True,
        )
        self.player_thread = threading.Thread(
            target=self._play_audio,
            daemon=True,
        )

        self.reader_thread.start()
        self.player_thread.start()

        print("Piper TTS ready.")

    def _read_audio(self):
        while not self.stop_event.is_set():
            data = self.process.stdout.read(4096)

            if not data:
                break

            self.audio_queue.put(data)

    def _play_audio(self):
        paplay = subprocess.Popen(
            [
                "paplay",
                "--raw",
                "--format=s16le",
                "--rate=22050",
                "--channels=1",
            ],
            stdin=subprocess.PIPE,
        )

        try:
            while not self.stop_event.is_set():
                try:
                    data = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if data is None:
                    break

                try:
                    paplay.stdin.write(data)
                    paplay.stdin.flush()
                except (BrokenPipeError, OSError):
                    break

        finally:
            try:
                paplay.stdin.close()
            except Exception:
                pass

            try:
                paplay.wait()
            except Exception:
                pass

    def speak(self, text):
        if not text.strip():
            return

        self.process.stdin.write(
            (text.strip() + "\n").encode("utf-8")
        )
        self.process.stdin.flush()

    def close(self):
        self.stop_event.set()

        try:
            self.audio_queue.put(None)
        except Exception:
            pass

        try:
            self.process.stdin.close()
        except Exception:
            pass

        try:
            self.process.terminate()
            self.process.wait(timeout=2)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass