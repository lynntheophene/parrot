import { state } from "./state.js";

import {
    setStatus,
    setListening
} from "./ui.js";


// ============================================
// STOP ALL ASSISTANT AUDIO
// ============================================

export function stopAssistantAudio() {

    console.log("STOP ASSISTANT AUDIO");

    // Invalidate the current response
    state.audioGeneration++;

    console.log(
        "Audio generation:",
        state.audioGeneration
    );

    // IMPORTANT:
    // Clear any sentences waiting to play
    state.audioQueue = [];

    console.log("Audio queue cleared");


    // Stop currently playing audio
    if (state.currentAudio) {

        console.log(
            "Stopping current Audio object"
        );

        try {

            state.currentAudio.pause();

            state.currentAudio.currentTime = 0;

            state.currentAudio.src = "";

            state.currentAudio.load();

        } catch (error) {

            console.warn(
                "Audio stop warning:",
                error
            );
        }

        state.currentAudio.onended = null;
        state.currentAudio.onerror = null;

        state.currentAudio = null;
    }


    // Release object URL
    if (state.currentAudioUrl) {

        console.log(
            "Releasing audio URL"
        );

        try {

            URL.revokeObjectURL(
                state.currentAudioUrl
            );

        } catch (error) {

            console.warn(
                "URL cleanup warning:",
                error
            );
        }

        state.currentAudioUrl = null;
    }

    state.audioPlaying = false;
}


// ============================================
// ADD AUDIO TO QUEUE
// ============================================

export function enqueueAudio(arrayBuffer) {

    console.log(
        "RECEIVED ASSISTANT AUDIO"
    );

    // Add this sentence to queue
    state.audioQueue.push(arrayBuffer);

    console.log(
        "Audio queue:",
        state.audioQueue.length
    );


    // Start playback only if nothing
    // is currently playing
    if (!state.audioPlaying) {

        playNextAudio();
    }
}


// ============================================
// PLAY NEXT AUDIO
// ============================================

async function playNextAudio() {

    // Prevent two audio objects
    // from playing simultaneously
    if (state.audioPlaying) {

        console.log(
            " Audio already playing"
        );

        return;
    }


    // Nothing left in queue
    if (state.audioQueue.length === 0) {

        console.log(
            "AUDIO QUEUE EMPTY"
        );

        state.currentAudio = null;
        state.currentAudioUrl = null;
        state.audioPlaying = false;

        setListening();

        return;
    }


    // Lock playback immediately
    state.audioPlaying = true;


    // Remember current generation
    const myGeneration =
        state.audioGeneration;


    // Take next sentence
    const arrayBuffer =
        state.audioQueue.shift();


    console.log(
        "PLAYING NEXT SENTENCE",
        "generation:",
        myGeneration,
        "remaining:",
        state.audioQueue.length
    );


    try {

        const blob = new Blob(
            [arrayBuffer],
            {
                type: "audio/wav"
            }
        );


        const url =
            URL.createObjectURL(blob);


        const audio =
            new Audio(url);


        state.currentAudioUrl = url;
        state.currentAudio = audio;


        audio.preload = "auto";


        // ====================================
        // AUDIO FINISHED
        // ====================================

        audio.onended = () => {

            console.log(
                " SENTENCE FINISHED"
            );


            try {

                URL.revokeObjectURL(url);

            } catch (error) {

                console.warn(
                    "URL cleanup warning:",
                    error
                );
            }


            // Only clear our own audio object
            if (
                state.currentAudio === audio
            ) {

                state.currentAudio = null;
                state.currentAudioUrl = null;
            }


            state.audioPlaying = false;


            // User interrupted us
            if (
                myGeneration !==
                state.audioGeneration
            ) {

                console.log(
                    " OLD GENERATION - STOPPING QUEUE"
                );

                return;
            }


            // Continue with next sentence
            playNextAudio();
        };


        // ====================================
        // AUDIO ERROR
        // ====================================

        audio.onerror = (error) => {

            console.error(
                " Audio playback error:",
                error
            );


            try {

                URL.revokeObjectURL(url);

            } catch (error) {

                console.warn(
                    "URL cleanup warning:",
                    error
                );
            }


            if (
                state.currentAudio === audio
            ) {

                state.currentAudio = null;
                state.currentAudioUrl = null;
            }


            state.audioPlaying = false;


            // Don't continue an old response
            if (
                myGeneration !==
                state.audioGeneration
            ) {

                return;
            }


            // Try next sentence
            playNextAudio();
        };


        // ====================================
        // START PLAYBACK
        // ====================================

        setStatus("Speaking...");


        console.log(
            " PLAYING AUDIO"
        );


        await audio.play();

    } catch (error) {

        console.error(
            "Audio playback error:",
            error
        );


        state.currentAudio = null;
        state.currentAudioUrl = null;
        state.audioPlaying = false;


        if (
            myGeneration !==
            state.audioGeneration
        ) {

            return;
        }


        playNextAudio();
    }
}