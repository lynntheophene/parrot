from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .vad import SileroVAD
from .stt import MoonshineSTT
from .llm import LocalLLM
from .tts import PiperTTS
import numpy as np
import asyncio
import threading
import time

SAMPLE_RATE = 16000
SILENCE_DURATION = 0.7
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


def sentence_chunks(token_stream):
    """
    Convert streamed LLM tokens into sentence-sized chunks.
    """

    buffer = ""

    for token in token_stream:

        buffer += token

        # Check the whole buffer, not just the latest token
        if buffer.rstrip().endswith((".", "!", "?")):

            sentence = buffer.strip()

            if sentence:
                yield sentence

            buffer = ""

    # Send remaining text
    if buffer.strip():
        yield buffer.strip()

async def sentence_chunks_async(token_stream):
    """
    Convert an async LLM token stream into sentence-sized chunks.
    """

    buffer = ""

    async for token in token_stream:

        buffer += token

        if buffer.rstrip().endswith((".", "!", "?")):

            sentence = buffer.strip()

            if sentence:
                yield sentence

            buffer = ""

    if buffer.strip():
        yield buffer.strip()      

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

async def async_llm_stream(llm, text, stop_event):
    """
    Runs the synchronous LLM stream in a background thread
    and forwards tokens into the asyncio event loop.
    """

    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def worker():
        try:
            for token in llm.stream(
                text,
                stop_event=stop_event
            ):
                asyncio.run_coroutine_threadsafe(
                    queue.put(("token", token)),
                    loop
                ).result()

            asyncio.run_coroutine_threadsafe(
                queue.put(("done", None)),
                loop
            ).result()

        except Exception as e:
            asyncio.run_coroutine_threadsafe(
                queue.put(("error", e)),
                loop
            ).result()

    asyncio.create_task(asyncio.to_thread(worker))

    completed = False

    try:
        while True:
            kind, value = await queue.get()

            if kind == "token":
                yield value

            elif kind == "done":
                completed = True
                break

            elif kind == "error":
                raise value

    finally:
        if not completed:
            stop_event.set()

async def process_utterance(
    websocket,
    audio,
    llm,
    tts,
    my_generation,
    get_generation
):

    try:
        request_start = time.perf_counter()
        # =========================
        # STT
        # =========================

        await websocket.send_json({
            "type": "processing",
            "stage": "stt"
        })

        stt_start = time.perf_counter() # stt timer

        text = await asyncio.to_thread(
            stt.transcribe,
            audio
        )
        stt_latency = time.perf_counter() - stt_start
        print(f"⏱ STT latency: {stt_latency:.3f}s")

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


        # ==========================================
        # STREAMING LLM + TTS
        # ==========================================

        if my_generation != get_generation():

            print(
                "OLD RESPONSE DISCARDED BEFORE LLM"
            )

            return


        await websocket.send_json({
            "type": "processing",
            "stage": "llm"
        })


        print(
            f"Starting streaming response "
            f"generation={my_generation}"
        )


        # Get the token generator.
        stop_event = threading.Event()

        full_response = ""

        token_stream = async_llm_stream(
            llm,
            text,
            stop_event
        )
        llm_start = time.perf_counter()
        first_sentence = True

        async for sentence in sentence_chunks_async(token_stream):

            # --------------------------------------
            # INTERRUPTION CHECK
            # --------------------------------------
            if first_sentence:
                llm_latency = time.perf_counter() - llm_start
                print(f"LLM → first sentence: {llm_latency:.3f}s")
                first_sentence = False

            if my_generation != get_generation():

                print("STREAM INTERRUPTED")

                tts.stop()

                return


            print(
                f"Sentence: {sentence}"
            )


            full_response += sentence + " "


            # --------------------------------------
            # SEND TEXT TO FRONTEND
            # --------------------------------------

            await websocket.send_json({
                "type": "response_chunk",
                "text": sentence
            })


            # --------------------------------------
            # TTS
            # --------------------------------------

            await websocket.send_json({
                "type": "processing",
                "stage": "tts"
            })


            tts_start = time.perf_counter()

            audio_bytes = await asyncio.to_thread(
                tts.generate,
                sentence
            )

            tts_latency = time.perf_counter() - tts_start

            print(f"TTS latency: {tts_latency:.3f}s")


            # --------------------------------------
            # INTERRUPTION CHECK
            # --------------------------------------

            if my_generation != get_generation():

                print(
                    "TTS RESULT DISCARDED"
                )

                tts.stop()

                return


            if not audio_bytes:

                continue


            print(
                "Sending sentence audio"
            )

            total_latency = time.perf_counter() - request_start

            print(
                f"TOTAL → first audio: "
                f"{total_latency:.3f}s"
            )

            await websocket.send_bytes(
                audio_bytes
            )


        # --------------------------------------
        # RESPONSE COMPLETE
        # --------------------------------------

        if my_generation != get_generation():

            return


        await websocket.send_json({
            "type": "response_complete",
            "text": full_response.strip()
        })


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