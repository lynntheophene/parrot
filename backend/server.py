from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .vad import SileroVAD
# from .stt import MoonshineSTT
from backend.parakeet_stt import ParakeetSTT
from .llm import LocalLLM
# from .tts import PiperTTS
from .tts import KokoroTTS
import numpy as np
import asyncio
import threading
import time

SAMPLE_RATE = 16000
SILENCE_DURATION = 0.6
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
# stt = MoonshineSTT()
stt = ParakeetSTT()

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
    Convert streamed LLM tokens into natural phrase-sized chunks.

    Flush when:
    - sentence-ending punctuation appears
    - a comma/semicolon/colon appears after enough words
    - the chunk gets too long
    """

    buffer = ""
    word_count = 0

    async for token in token_stream:
        buffer += token
        word_count = len(buffer.strip().split())

        stripped = buffer.rstrip()

        # Strong boundaries
        if stripped.endswith((".", "!", "?")):
            yield stripped
            buffer = ""
            word_count = 0
            continue

        # Medium boundaries
        if (
            word_count >= 4
            and stripped.endswith((",", ";", ":"))
        ):
            yield stripped
            buffer = ""
            word_count = 0
            continue

        # Safety fallback
        if word_count >= 7:
            yield stripped
            buffer = ""
            word_count = 0

    # Send remaining text
    if buffer.strip():
        yield buffer.strip()    

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await websocket.accept()

    print("Client connected")

    session_llm = LocalLLM()
    # session_tts = PiperTTS()
    session_tts = KokoroTTS()

    speech_audio = []

    speaking = False
    silence_chunks = 0

    processing_task = None

    # Every new user utterance gets a new generation ID.
    # Old responses become invalid immediately when the user speaks.
    generation = 0
    # Buffer incoming browser audio until we have a full VAD chunk
    audio_buffer = np.array([], dtype=np.float32)

    try:

        while True:

            data = await websocket.receive_bytes()
            print("AUDIO RECEIVED:", len(data), "bytes")
            audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

            if len(audio) == 0:
                continue
             # Add new audio to the persistent buffer
            audio_buffer = np.concatenate([
                audio_buffer,
                audio
            ])

            # Process complete VAD chunks
            while len(audio_buffer) >= VAD_CHUNK_SIZE:

                chunk = audio_buffer[:VAD_CHUNK_SIZE]

                audio_buffer = audio_buffer[VAD_CHUNK_SIZE:]



            # for i in range(
            #     0,
            #     len(audio),
            #     VAD_CHUNK_SIZE
            # ):

                # chunk = audio[
                #     i:i + VAD_CHUNK_SIZE
                # ]

                # if len(chunk) != VAD_CHUNK_SIZE:
                #     continue

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

        stt_start = time.perf_counter()

        text = await asyncio.to_thread(
            stt.transcribe,
            audio
        )

        stt_latency = time.perf_counter() - stt_start

        print(
            f"⏱ STT latency: "
            f"{stt_latency:.3f}s"
        )

        # Check interruption
        if my_generation != get_generation():
            print("OLD RESPONSE DISCARDED AFTER STT")
            return

        if not text.strip():
            await websocket.send_json({
                "type": "empty"
            })
            return

        print(f"User: {text}")

        await websocket.send_json({
            "type": "transcript",
            "text": text
        })

        # =========================
        # LLM
        # =========================

        if my_generation != get_generation():
            print("OLD RESPONSE DISCARDED BEFORE LLM")
            return

        await websocket.send_json({
            "type": "processing",
            "stage": "llm"
        })

        print(
            f"Starting streaming response "
            f"generation={my_generation}"
        )

        stop_event = threading.Event()

        full_response = ""

        token_stream = async_llm_stream(
            llm,
            text,
            stop_event
        )

        # =========================
        # TTS QUEUE
        # =========================

        tts_queue = asyncio.Queue()

        first_chunk = True
        first_audio_sent = False

        async def tts_worker():

            nonlocal first_audio_sent

            while True:

                sentence = await tts_queue.get()

                if sentence is None:
                    tts_queue.task_done()
                    break

                try:

                    # Check interruption
                    if my_generation != get_generation():
                        print("TTS WORKER INTERRUPTED")
                        return

                    print(
                        f"🎙 TTS chunk: {sentence}"
                    )

                    await websocket.send_json({
                        "type": "processing",
                        "stage": "tts"
                    })

                    tts_start = time.perf_counter()

                    audio_bytes = await asyncio.to_thread(
                        tts.generate,
                        sentence
                    )

                    tts_latency = (
                        time.perf_counter()
                        - tts_start
                    )

                    print(
                        f"⏱ TTS latency: "
                        f"{tts_latency:.3f}s"
                    )

                    # Check interruption again
                    if my_generation != get_generation():

                        print(
                            "TTS RESULT DISCARDED"
                        )

                        tts.stop()
                        return

                    if not audio_bytes:
                        continue

                    # First audio latency
                    if not first_audio_sent:

                        total_latency = (
                            time.perf_counter()
                            - request_start
                        )

                        print(
                            f"⏱ TOTAL → first audio: "
                            f"{total_latency:.3f}s"
                        )

                        first_audio_sent = True

                    print(
                        "Sending chunk audio"
                    )

                    await websocket.send_bytes(
                        audio_bytes
                    )

                finally:
                    tts_queue.task_done()

        # Start TTS worker
        tts_task = asyncio.create_task(
            tts_worker()
        )

        # =========================
        # STREAM LLM
        # =========================

        llm_start = time.perf_counter()

        async for sentence in sentence_chunks_async(
            token_stream
        ):

            # Interruption check
            if my_generation != get_generation():

                print(
                    "STREAM INTERRUPTED"
                )

                stop_event.set()
                tts.stop()

                return

            if first_chunk:

                llm_latency = (
                    time.perf_counter()
                    - llm_start
                )

                print(
                    f"⏱ LLM → first chunk: "
                    f"{llm_latency:.3f}s"
                )

                first_chunk = False

            print(
                f"LLM chunk: {sentence}"
            )

            full_response += sentence + " "

            # Send text immediately
            await websocket.send_json({
                "type": "response_chunk",
                "text": sentence
            })

            # Put chunk into TTS queue
            await tts_queue.put(sentence)

        # =========================
        # WAIT FOR TTS
        # =========================

        await tts_queue.join()

        # Tell worker to stop
        await tts_queue.put(None)

        await tts_task

        # =========================
        # RESPONSE COMPLETE
        # =========================

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

        tts.stop()
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