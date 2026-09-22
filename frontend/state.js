export const state = {
    websocket: null,

    audioContext: null,
    microphone: null,
    processor: null,

    currentAudio: null,
    currentAudioUrl: null,

    // Changes whenever assistant audio is interrupted.
    audioGeneration: 0,

    started: false
};