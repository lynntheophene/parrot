from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .vad import SileroVAD
from .stt import MoonshineSTT
from .llm import LocalLLM
from .tts import PiperTTS
import numpy as np
import asyncio

SAMPLE_RATE = 16000
SILENCE_DURATION = 1.0
VAD_CHUNK_SIZE = 512

SILENCE_CHUNKS = int(
    SILENCE_DURATION * SAMPLE_RATE / VAD_CHUNK_SIZE
)

app = FastAPI(
    title="Voice Agent API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


print("Loading AI models...")

vad = SileroVAD()
stt = MoonshineSTT()

print("All models loaded.")


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "voice-agent"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await websocket.accept()

    print("Client connected")

    session_llm = LocalLLM()
    session_tts = PiperTTS()

    speech_audio = []

    speaking = False
    silence_chunks = 0

    processing_task = None

    # Every new user utterance gets a new generation ID.
    # Old responses become invalid immediately when the user speaks.
    generation = 0

    try:

        while True:

            data = await websocket.receive_bytes()

            audio = np.frombuffer(
                data,
                dtype=np.float32
            )

            if len(audio) == 0:
                continue

            for i in range(
                0,
                len(audio),
                VAD_CHUNK_SIZE
            ):

                chunk = audio[
                    i:i + VAD_CHUNK_SIZE
                ]

                if len(chunk) != VAD_CHUNK_SIZE:
                    continue

                probability = vad.speech_probability(
                    chunk
                )

                speech = probability > 0.6

                # =========================
                # SPEECH START
                # =========================

                if speech and not speaking:

                    print("================================")
                    print("SPEECH START")
                    print("INTERRUPTING CURRENT RESPONSE")
                    print("================================")

                    speaking = True

                    speech_audio = [chunk]

                    silence_chunks = 0

                    # Invalidate EVERYTHING from the
                    # previous response.
                    generation += 1

                    current_generation = generation

                    print(
                        f"New generation: {generation}"
                    )

                    # Stop Piper immediately.
                    session_tts.stop()

                    # Cancel async processing task.
                    if (
                        processing_task is not None
                        and not processing_task.done()
                    ):

                        print(
                            "Cancelling old processing task..."
                        )

                        processing_task.cancel()

                    processing_task = None

                    # Tell browser to stop audio.
                    await websocket.send_json({
                        "type": "interrupt",
                        "generation": generation
                    })

                    # Tell browser speech started.
                    await websocket.send_json({
                        "type": "speech_start"
                    })


                # =========================
                # SPEECH CONTINUES
                # =========================

                elif speech and speaking:

                    speech_audio.append(chunk)

                    silence_chunks = 0


                # =========================
                # SILENCE
                # =========================

                elif not speech and speaking:

                    speech_audio.append(chunk)

                    silence_chunks += 1

                    if silence_chunks >= SILENCE_CHUNKS:

                        print("SPEECH END")

                        speaking = False

                        silence_chunks = 0

                        utterance = np.concatenate(
                            speech_audio
                        )

                        speech_audio = []

                        # Capture the generation for
                        # THIS utterance.
                        utterance_generation = generation

                        print(
                            "Processing generation:",
                            utterance_generation
                        )

                        processing_task = asyncio.create_task(
                            process_utterance(
                                websocket,
                                utterance,
                                session_llm,
                                session_tts,
                                utterance_generation,
                                lambda: generation
                            )
                        )

    except WebSocketDisconnect:

        print("Client disconnected")

    except Exception as e:

        print(
            f"WebSocket error: {e}"
        )

    finally:

        print("Cleaning up session")

        session_tts.stop()

        if (
            processing_task is not None
            and not processing_task.done()
        ):

            processing_task.cancel()

        session_tts.close()

        print("Session cleaned up")


async def process_utterance(
    websocket,
    audio,
    llm,
    tts,
    my_generation,
    get_generation
):

    try:

        # =========================
        # STT
        # =========================

        await websocket.send_json({
            "type": "processing",
            "stage": "stt"
        })

        text = await asyncio.to_thread(
            stt.transcribe,
            audio
        )

        # Check whether user interrupted us
        if my_generation != get_generation():

            print(
                "OLD RESPONSE DISCARDED AFTER STT"
            )

            return

        if not text.strip():

            await websocket.send_json({
                "type": "empty"
            })

            return

        print(
            f"User: {text}"
        )

        await websocket.send_json({
            "type": "transcript",
            "text": text
        })


        # =========================
        # LLM
        # =========================

        if my_generation != get_generation():

            print(
                "OLD RESPONSE DISCARDED BEFORE LLM"
            )

            return

        await websocket.send_json({
            "type": "processing",
            "stage": "llm"
        })

        response = await asyncio.to_thread(
            llm.generate,
            text
        )

        # CRITICAL CHECK
        if my_generation != get_generation():

            print(
                "OLD LLM RESPONSE DISCARDED"
            )

            return

        print(
            f"Assistant: {response}"
        )

        await websocket.send_json({
            "type": "response",
            "text": response
        })


        # =========================
        # TTS
        # =========================

        if my_generation != get_generation():

            print(
                "OLD RESPONSE DISCARDED BEFORE TTS"
            )

            return

        await websocket.send_json({
            "type": "processing",
            "stage": "tts"
        })

        audio_bytes = await asyncio.to_thread(
            tts.generate,
            response
        )

        # CRITICAL CHECK
        #
        # User may have interrupted while Piper
        # was generating the WAV.
        #

        if my_generation != get_generation():

            print(
                "OLD TTS AUDIO DISCARDED"
            )

            return

        if not audio_bytes:

            return

        print(
            f"Sending audio generation {my_generation}"
        )

        await websocket.send_bytes(
            audio_bytes
        )

        await websocket.send_json({
            "type": "done"
        })


    except asyncio.CancelledError:

        print(
            f"Processing cancelled "
            f"(generation {my_generation})"
        )

        raise


    except Exception as e:

        print(
            f"Processing error: {e}"
        )

        try:

            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })

        except Exception:
            pass