#!/bin/bash

echo "======================================"
echo "       LOCAL VOICE AGENT STARTUP"
echo "======================================"

echo "Starting Llama server..."

gnome-terminal -- bash -c '
echo "===== LLAMA SERVER - T1 ====="

export LD_LIBRARY_PATH=/opt/rocm/lib:/opt/rocm/core-10.0/lib:$LD_LIBRARY_PATH

~/llama.cpp/build/bin/llama-server \
    -m ~/c_ai/models/qwen2.5-3b-instruct-q4_k_m.gguf \
    -c 2048 \
    -ngl 99 \
    --host 127.0.0.1 \
    --port 8080

echo "Llama server stopped."
exec bash
'

sleep 3

# echo "Starting Fish Speech S1-mini..."

# gnome-terminal -- bash -c '
# echo "===== FISH SPEECH S1-MINI - T2 ====="

# cd ~/fish-speech-s1

# docker compose -f compose.rocm-s1.yml up

# echo "Fish Speech stopped."
# exec bash
# '

# sleep 8

echo "Starting Voice Agent..."

gnome-terminal -- bash -c '
echo "===== VOICE AGENT - T3 ====="

source ~/whisper-rocm/bin/activate

cd ~/voice-agent

python main.py

echo "Voice agent stopped."
exec bash
'

echo "Startup complete."
