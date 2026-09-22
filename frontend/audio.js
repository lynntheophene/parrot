import { state } from "./state.js";
import {
    setStatus,
    setListening
} from "./ui.js";


export function stopAssistantAudio() {

    console.log(" STOP ASSISTANT AUDIO");

    // Invalidate old audio.
    state.audioGeneration++;

    console.log(
        "Audio generation:",
        state.audioGeneration
    );


    if (state.currentAudio) {

        console.log(
            " Stopping current Audio object"
        );

        try {

            state.currentAudio.pause();

            state.currentAudio.currentTime = 0;

            // Completely detach audio.
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
}


export async function playAudio(arrayBuffer) {

    console.log(
        " RECEIVED ASSISTANT AUDIO"
    );


    // Kill anything currently playing.
    stopAssistantAudio();


    // Remember which generation this audio belongs to.
    const myGeneration =
        state.audioGeneration;


    try {

        const blob = new Blob(
            [arrayBuffer],
            {
                type: "audio/wav"
            }
        );


        state.currentAudioUrl =
            URL.createObjectURL(blob);


        state.currentAudio =
            new Audio(
                state.currentAudioUrl
            );


        state.currentAudio.preload =
            "auto";


        // ==============================
        // AUDIO FINISHED
        // ==============================

        state.currentAudio.onended =
            () => {

                console.log(
                    "AUDIO FINISHED"
                );


                if (
                    state.currentAudioUrl
                ) {

                    URL.revokeObjectURL(
                        state.currentAudioUrl
                    );
                }


                state.currentAudio = null;

                state.currentAudioUrl = null;

                setListening();
            };


        // ==============================
        // AUDIO ERROR
        // ==============================

        state.currentAudio.onerror =
            (error) => {

                console.error(
                    " Audio playback error:",
                    error
                );

                stopAssistantAudio();

                setListening();
            };


        // ==============================
        // INTERRUPTION CHECK
        // ==============================

        if (
            myGeneration !==
            state.audioGeneration
        ) {

            console.log(
                " Audio invalidated before playback"
            );

            stopAssistantAudio();

            return;
        }


        setStatus("Speaking...");


        console.log(
            " PLAYING ASSISTANT AUDIO",
            "generation:",
            myGeneration
        );


        await state.currentAudio.play();

    } catch (error) {

        console.error(
            "Audio playback error:",
            error
        );

        stopAssistantAudio();

        setListening();
    }
}