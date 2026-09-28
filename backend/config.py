import os
from pathlib import Path


# ==========================
# Base paths
# ==========================

BASE_DIR = Path(
    os.getenv("JARVIS_HOME", "~/parrot")
).expanduser()

MODELS_DIR = BASE_DIR / "models"


# ==========================
# ASR - Parakeet
# ==========================

PARAKEET_MODEL = os.getenv(
    "PARAKEET_MODEL",
    str(
        MODELS_DIR /
        "parakeet/parakeet-tdt-0.6b-v3-asr-q8_0.gguf"
    )
)

ASR_DEVICE = os.getenv(
    "ASR_DEVICE",
    "cuda:0"
)


# ==========================
# LLM - llama.cpp server
# ==========================

LLM_URL = os.getenv(
    "LLM_URL",
    "http://127.0.0.1:8080/v1/chat/completions"
)

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "qwen2.5-3b-instruct"
)


# ==========================
# TTS - Kokoro
# ==========================

KOKORO_REPO = os.getenv(
    "KOKORO_REPO",
    "hexgrad/Kokoro-82M"
)

KOKORO_LANG = os.getenv(
    "KOKORO_LANG",
    "a"
)

KOKORO_VOICE = os.getenv(
    "KOKORO_VOICE",
    "af_sky"
)

KOKORO_DEVICE = os.getenv(
    "KOKORO_DEVICE",
    "cuda"
)


# ==========================
# Audio
# ==========================

INPUT_SAMPLE_RATE = 16000

OUTPUT_SAMPLE_RATE = 24000

CHANNELS = 1


# ==========================
# VAD
# ==========================

VAD_CHUNK_SIZE = 512

SILENCE_DURATION = 1.0


# ==========================
# Server
# ==========================

HOST = os.getenv(
    "HOST",
    "0.0.0.0"
)

PORT = int(
    os.getenv(
        "PORT",
        8000
    )
)
