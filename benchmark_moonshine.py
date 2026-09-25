import time
import wave
import numpy as np

from stt import MoonshineSTT


AUDIO_FILE = "/home/mogu/voice-agent/test_mono.wav"


def load_wav(path):
    with wave.open(path, "rb") as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        frames = wf.readframes(wf.getnframes())

    if sample_width != 2:
        raise RuntimeError(f"Expected 16-bit WAV, got {sample_width * 8}-bit")

    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

    if channels != 1:
        raise RuntimeError(f"Expected mono WAV, got {channels} channels")

    return audio, sample_rate


audio, sample_rate = load_wav(AUDIO_FILE)

duration = len(audio) / sample_rate

print("=" * 50)
print("MOONSHINE BENCHMARK")
print("=" * 50)
print(f"Audio duration: {duration:.2f} sec")
print(f"Sample rate:    {sample_rate} Hz")
print()

stt = MoonshineSTT()

# Warm-up
print("Warming up...")
stt.transcribe(audio)

# Actual benchmark
start = time.perf_counter()

text = stt.transcribe(audio)

elapsed = time.perf_counter() - start

rtf = elapsed / duration
speed = duration / elapsed

print()
print("=" * 50)
print("RESULT")
print("=" * 50)
print(f"Transcript:     {text}")
print(f"Inference:      {elapsed:.3f} sec")
print(f"Audio duration: {duration:.3f} sec")
print(f"RTF:            {rtf:.3f}")
print(f"Speed:          {speed:.2f}x real-time")
print("=" * 50)

stt.close()
