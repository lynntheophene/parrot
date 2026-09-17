import time

from audio import start_microphone, get_audio, add_to_vad_buffer
from vad import SileroVAD
from stt import MoonshineSTT


SAMPLE_RATE = 16000


print("Starting components...")

vad = SileroVAD()
stt = MoonshineSTT()

stream = start_microphone()

print()
print("=" * 50)
print("VOICE TEST")
print("=" * 50)
print("Speak into your microphone.")
print("Press Ctrl+C to stop.")
print("=" * 50)
print()


try:
    while True:

        # Get audio from your existing microphone pipeline
        audio = get_audio()

        # Convert to the 512-sample VAD chunks
        vad_chunk = add_to_vad_buffer(audio)

        if vad_chunk is None:
            continue

        # Silero VAD
        probability = vad.speech_probability(vad_chunk)

        print(
            f"\rVAD: {probability:.2f}",
            end="",
            flush=True
        )

        # Feed audio to Moonshine
        stt.feed(vad_chunk)

        # Ask Moonshine for current text
        text = stt.get_text()

        if text.strip():
            print(f"\n📝 {text}")

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    stream.stop()
    stream.close()
    stt.close()
