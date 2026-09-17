import queue
import sys
import numpy as np
import sounddevice as sd
from scipy.signal import resample


# ==============================
# Configuration
# ==============================

INPUT_SAMPLE_RATE = 44100
OUTPUT_SAMPLE_RATE = 16000
BLOCK_SIZE = 512
VAD_CHUNK_SIZE = 512

# Queue between microphone and processing
audio_queue = queue.Queue()
vad_buffer = np.array([], dtype=np.float32)


# ==============================
# Microphone callback , also put microphone data into queue
# ==============================

def audio_callback(indata, frames, time, status):

    if status:
        print(status, file=sys.stderr)

    # Make our own copy of the microphone data
    audio_queue.put(indata.copy())


# ==============================
# Start microphone
# ==============================

def start_microphone():

    stream = sd.InputStream(
        samplerate=INPUT_SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        channels=1,
        dtype="float32",
        callback=audio_callback,
    )

    stream.start()

    return stream


# ==============================
# Get audio from queue
# ==============================

def get_audio():

    # Wait until microphone puts something
    data_chunk = audio_queue.get()

    # Convert to mono
    if data_chunk.ndim > 1 and data_chunk.shape[1] > 1:
        mono_chunk = np.mean(data_chunk, axis=1)
    else:
        mono_chunk = data_chunk.flatten()

    # Resample 44.1 kHz → 16 kHz
    num_samples = int(
        len(mono_chunk)
        * OUTPUT_SAMPLE_RATE
        / INPUT_SAMPLE_RATE
    )

    resampled_chunk = resample(
        mono_chunk,
        num_samples
    )

    return resampled_chunk

def add_to_vad_buffer(audio): # this adds audio to the VAD buffer and returns a chunk of audio if enough samples are available

    global vad_buffer

    # Add new audio to existing buffer
    vad_buffer = np.concatenate(
        [vad_buffer, audio]
    )

    # Check whether we have enough audio
    if len(vad_buffer) >= VAD_CHUNK_SIZE:

        # Take the first 512 samples
        vad_chunk = vad_buffer[:VAD_CHUNK_SIZE]

        # Remove those samples from the buffer
        vad_buffer = vad_buffer[VAD_CHUNK_SIZE:]

        return vad_chunk

    # Not enough audio yet
    return None    