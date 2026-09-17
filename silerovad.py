import queue
import sys
import numpy as np
import sounddevice as sd
from scipy.signal import resample

# 1. Configuration
INPUT_SAMPLE_RATE = 44100  # Your microphone's native rate
OUTPUT_SAMPLE_RATE = 16000  # Your target live rate
BLOCK_SIZE = 512 # Size of each live audio chunk

# Queue to pass audio data from the mic thread to the processing thread
audio_queue = queue.Queue()


# 2. Define the Live Callback
def audio_callback(indata, frames, time, status):
    """This function is called for every audio chunk captured by the mic."""
    if status:
        print(status, file=sys.stderr)

    # Put a copy of the incoming audio block into the queue
    audio_queue.put(indata.copy())


# 3. Start the Live Stream
try:
    # Open the input stream (requesting 1 channel attempts mono at hardware level)
    with sd.InputStream(
        samplerate=INPUT_SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        channels=1,
        dtype="float32",
        callback=audio_callback,
    ):
        print("Recording live... Press Ctrl+C to stop.")

        # 4. Infinite Processing Loop
        while True:
            # Wait for the next chunk of audio from the queue
            data_chunk = audio_queue.get()

            # A. Live Mono Conversion (Safeguard if hardware forces stereo)
            if data_chunk.ndim > 1 and data_chunk.shape[1] > 1:
                mono_chunk = np.mean(data_chunk, axis=1)
            else:
                mono_chunk = data_chunk.flatten()

            # B. Live Resampling
            # Calculate how many samples the output chunk should have
            num_samples = int(
                len(mono_chunk) * OUTPUT_SAMPLE_RATE / INPUT_SAMPLE_RATE
            )
            resampled_chunk = resample(mono_chunk, num_samples)

            # C. Consume Live Data
            # 'resampled_chunk' is your live, mono, resampled audio block
            # (Ready for speech-to-text, network sockets, model inference, etc.)
            print(f"Processed chunk size: {len(resampled_chunk)} samples")
            print(
            f"Input: {len(mono_chunk)} samples | "
            f"Output: {len(resampled_chunk)} samples"
)

except KeyboardInterrupt:
    print("\nLive stream stopped.")
except Exception as e:
    print(f"Error: {e}")
