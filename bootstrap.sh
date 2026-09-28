#!/bin/bash

set -e

PROJECT="/home/parrot"
PYTHON="/root/miniconda3/envs/py3.10/bin/python3"

cd "$PROJECT"

echo "======================================"
echo "        PARROT BOOTSTRAP"
echo "======================================"

echo "[1/5] Checking system dependencies..."

apt-get update -qq

apt-get install -y \
    build-essential \
    cmake \
    curl \
    libsentencepiece0 \
    libsentencepiece-dev

echo "[2/5] Checking Python environment..."

if ! "$PYTHON" -c "
import fastapi
import uvicorn
import websockets
import kokoro
import sentencepiece
import silero_vad
import torch
" >/dev/null 2>&1; then

    echo "Missing Python dependencies."
    echo "Restoring from requirements-working.txt..."

    "$PYTHON" -m pip install \
        -r "$PROJECT/requirements-working.txt"

else
    echo "Python environment OK."
fi

echo "[3/5] Verifying GPU..."

"$PYTHON" - <<'PY'
import torch

print("PyTorch:", torch.__version__)
print("CUDA:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
else:
    raise RuntimeError("CUDA GPU not available")
PY

echo "[4/5] Verifying Parakeet..."

NEMO="/home/parrot/NeMo-Speech.cpp/build/cuda-asr/bin/nemo-speech"
PARAKEET="/home/parrot/models/parakeet/parakeet-tdt-0.6b-v3-asr-q8_0.gguf"

if [ ! -x "$NEMO" ]; then
    echo "ERROR: NeMo-Speech.cpp binary missing:"
    echo "$NEMO"
    exit 1
fi

if [ ! -f "$PARAKEET" ]; then
    echo "ERROR: Parakeet model missing:"
    echo "$PARAKEET"
    exit 1
fi

"$NEMO" model info "$PARAKEET" >/dev/null

echo "Parakeet OK."

echo "[5/5] Starting Parrot..."

# ======================================
# LLM
# ======================================

if curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
    echo "llama-server already running."
else
    echo "Starting llama-server..."

    nohup "$PROJECT/llama.cpp/build/bin/llama-server" \
        -m "$PROJECT/models/llm/qwen2.5-3b-instruct-q4_k_m.gguf" \
        --host 127.0.0.1 \
        --port 8080 \
        -ngl 99 \
        > "$PROJECT/llama-server.log" 2>&1 &

    echo "Waiting for llama-server..."

    for i in {1..60}; do
        if curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
            echo "llama-server ready."
            break
        fi
        sleep 1
    done

    if ! curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
        echo "ERROR: llama-server failed to start."
        tail -30 "$PROJECT/llama-server.log"
        exit 1
    fi
fi


# ======================================
# FRONTEND
# ======================================

if curl -sf http://127.0.0.1:3000/ >/dev/null 2>&1; then
    echo "Frontend already running."
else
    echo "Starting frontend..."

    nohup "$PYTHON" -m http.server 3000 \
        --directory "$PROJECT/frontend" \
        --bind 0.0.0.0 \
        > "$PROJECT/frontend.log" 2>&1 &

    sleep 2

    if curl -sf http://127.0.0.1:3000/ >/dev/null 2>&1; then
        echo "Frontend ready."
    else
        echo "WARNING: Frontend failed to start."
        tail -30 "$PROJECT/frontend.log"
    fi
fi


# ======================================
# BACKEND
# ======================================

if curl -sf http://127.0.0.1:8000/docs >/dev/null 2>&1; then
    echo "Backend already running."
else
    echo "Starting backend..."

    nohup "$PYTHON" -m uvicorn backend.server:app \
        --host 0.0.0.0 \
        --port 8000 \
        > "$PROJECT/backend.log" 2>&1 &

    echo "Waiting for backend models to load..."

    BACKEND_READY=0

    for i in {1..180}; do
        if curl -sf http://127.0.0.1:8000/docs >/dev/null 2>&1; then
            BACKEND_READY=1
            echo "Backend ready."
            break
        fi

        sleep 1

        if (( i % 15 == 0 )); then
            echo "Backend still loading... ${i}s"
        fi
    done

    if [ "$BACKEND_READY" -ne 1 ]; then
        echo "WARNING: Backend is still not ready after 180 seconds."
        echo "The process may still be loading models."
        echo "Check:"
        echo "  $PROJECT/backend.log"
    fi
fi


echo ""
echo "======================================"
echo "       PARROT READY"
echo "======================================"

echo ""
echo "Services:"
echo "  LLM:      http://127.0.0.1:8080"
echo "  Backend:  http://127.0.0.1:8000"
echo "  Frontend: http://127.0.0.1:3000"

echo ""
echo "Processes:"
pgrep -af "llama-server" || true
pgrep -af "uvicorn" || true
pgrep -af "http.server 3000" || true

echo ""
echo "Logs:"
echo "  $PROJECT/llama-server.log"
echo "  $PROJECT/backend.log"
echo "  $PROJECT/frontend.log"

echo ""
echo "======================================"