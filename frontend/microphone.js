
import { state } from "./state.js";

const TARGET_SAMPLE_RATE = 16000;

export async function startMicrophone(sendAudio) {
    console.log("Starting microphone...");

    // Ask the browser/OS for its best available microphone
    // with hardware/browser echo cancellation enabled.
    const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
            channelCount: { ideal: 1 },
            echoCancellation: { ideal: true },
            noiseSuppression: { ideal: true },
            autoGainControl: { ideal: true }
        }
    });

    const track = stream.getAudioTracks()[0];

    console.log("Microphone:", track.label);
    console.log("Microphone settings:", track.getSettings());

    // Use the browser's native audio rate.
    // Do NOT force 16 kHz here.
    const nativeSampleRate =
        track.getSettings().sampleRate ||
        48000;

    state.audioContext = new AudioContext({
        sampleRate: nativeSampleRate
    });

    console.log(
        "Browser audio sample rate:",
        state.audioContext.sampleRate
    );

    state.microphone =
        state.audioContext.createMediaStreamSource(stream);

    /*
     * Temporary processing stage.
     *
     * We keep ScriptProcessor for now because your existing
     * backend already expects raw PCM over WebSocket.
     *
     * Once the complete browser pipeline is working,
     * we can replace this with AudioWorklet for lower latency.
     */
    state.processor =
        state.audioContext.createScriptProcessor(
            1024,
            1,
            1
        );

    state.processor.onaudioprocess = (event) => {
        console.log("Audio callback running");
        if (
            !state.websocket ||
            state.websocket.readyState !== WebSocket.OPEN
        ) {
            return;
        }

        const input =
            event.inputBuffer.getChannelData(0);

        // Browser-native Float32 PCM
        const inputCopy = new Float32Array(input);

        // Resample to 16 kHz for the backend.
        const output =
            resampleTo16k(
                inputCopy,
                state.audioContext.sampleRate
            );
        const pcm16 = new Int16Array(output.length);

        for (let i = 0; i < output.length; i++) {
            const sample = Math.max(-1, Math.min(1, output[i]));

            pcm16[i] = sample < 0
                ? sample * 0x8000
                : sample * 0x7fff;
}        
        sendAudio(pcm16.buffer);
    };

    state.microphone.connect(state.processor);

    /*
     * ScriptProcessor needs to be connected to an output
     * to remain active in some browsers.
     *
     * We do NOT want to play the microphone back to the user,
     * so connect through a zero-gain node.
     */
    const silentGain =
        state.audioContext.createGain();

    silentGain.gain.value = 0;

    state.processor.connect(silentGain);
    silentGain.connect(
        state.audioContext.destination
    );

    state.microphoneStream = stream;
    state.microphoneTrack = track;
    state.microphoneSilentGain = silentGain;

    console.log("Microphone ready");
    console.log(
        "Echo cancellation:",
        track.getSettings().echoCancellation
    );
    console.log(
        "Noise suppression:",
        track.getSettings().noiseSuppression
    );
    console.log(
        "Auto gain:",
        track.getSettings().autoGainControl
    );
}


function resampleTo16k(input, inputRate) {
    if (inputRate === TARGET_SAMPLE_RATE) {
        return input;
    }

    const outputLength =
        Math.round(
            input.length *
            TARGET_SAMPLE_RATE /
            inputRate
        );

    const output =
        new Float32Array(outputLength);

    const ratio =
        inputRate / TARGET_SAMPLE_RATE;

    for (let i = 0; i < outputLength; i++) {
        const position = i * ratio;

        const index = Math.floor(position);

        const fraction = position - index;

        const sample1 =
            input[index] ?? 0;

        const sample2 =
            input[index + 1] ?? sample1;

        output[i] =
            sample1 +
            (sample2 - sample1) * fraction;
    }

    return output;
}


export function stopMicrophone() {
    console.log("Stopping microphone...");

    if (state.processor) {
        state.processor.disconnect();
        state.processor = null;
    }

    if (state.microphoneSilentGain) {
        state.microphoneSilentGain.disconnect();
        state.microphoneSilentGain = null;
    }

    if (state.microphone) {
        state.microphone.disconnect();
        state.microphone = null;
    }

    if (state.microphoneStream) {
        state.microphoneStream
            .getTracks()
            .forEach(track => track.stop());

        state.microphoneStream = null;
    }

    if (state.audioContext) {
        state.audioContext.close();
        state.audioContext = null;
    }

    state.microphoneTrack = null;
}
