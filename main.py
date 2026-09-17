from audio import start_microphone, get_audio, add_to_vad_buffer
from vad import SileroVAD
from stt import MoonshineSTT
from llm import LocalLLM
import numpy as np
from tts import PiperTTS


SAMPLE_RATE = 16000

SILENCE_DURATION = 1

VAD_CHUNK_SIZE = 512

SILENCE_CHUNKS = int(
    SILENCE_DURATION * SAMPLE_RATE / VAD_CHUNK_SIZE
)


def main():
    print("Starting microphone...")
    stream = start_microphone()

    print("Loading VAD...")
    vad = SileroVAD()

    print("Starting Moonshine...")
    stt = MoonshineSTT()

    print("Starting LLM...")
    llm = LocalLLM()

    print("Starting Piper...")
    tts = PiperTTS()

    print()
    print("==============================")
    print("       VOICE ASSISTANT")
    print("==============================")
    print("Listening...")
    print("Press Ctrl+C to stop.\n")

    speaking = False
    speech_audio = []
    silence_chunks = 0

    try:
        while True:

            # -------------------------
            # Get microphone audio
            # -------------------------

            audio = get_audio()

            vad_chunk = add_to_vad_buffer(audio)

            if vad_chunk is None:
                continue

            # -------------------------
            # VAD
            # -------------------------

            probability = vad.speech_probability(vad_chunk)

            speech = probability > 0.6

            # -------------------------
            # Speech started
            # -------------------------

            if speech and not speaking:

                print("\nSPEECH START")

                speaking = True
                speech_audio = []
                silence_chunks = 0

                speech_audio.append(vad_chunk)

            # -------------------------
            # Continue speech
            # -------------------------

            elif speech and speaking:

                speech_audio.append(vad_chunk)

                silence_chunks = 0

            # -------------------------
            # Silence
            # -------------------------

            elif not speech and speaking:

                speech_audio.append(vad_chunk)

                silence_chunks += 1

                # -------------------------
                # Utterance finished
                # -------------------------

                if silence_chunks >= SILENCE_CHUNKS:

                    print("SPEECH END")

                    speaking = False
                    silence_chunks = 0

                    utterance = np.concatenate(
                        speech_audio
                    )

                    duration = len(utterance) / SAMPLE_RATE

                    print(
                        f"Utterance: "
                        f"{len(utterance)} samples "
                        f"({duration:.2f} seconds)"
                    )

                    # -------------------------
                    # STT
                    # -------------------------

                    # stt.feed(utterance)

                    text = stt.transcribe(utterance)

                    if text.strip():

                        print(f"You: {text}")

                        # -------------------------
                        # LLM
                        # -------------------------

                        response = llm.generate(text)

                        print(
                            f"Assistant: {response}"
                        )

                        # -------------------------
                        # Piper
                        # -------------------------

                        tts.speak(response)

                    else:

                        print("No transcription")

                    speech_audio = []

    except KeyboardInterrupt:

        print("\nStopping...")

    finally:

        stream.stop()
        stream.close()

        tts.close()
        stt.close()


if __name__ == "__main__":
    main()