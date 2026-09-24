import { state } from "./state.js";

import {
    setStatus,
    setListening,
    setProcessing,
    addMessage
} from "./ui.js";

import {
    stopAssistantAudio,
    enqueueAudio
} from "./audio.js";


export function connectWebSocket() {

    return new Promise(
        (resolve, reject) => {

            console.log(
                " Connecting WebSocket..."
            );


            state.websocket =
                new WebSocket(
                    "ws://127.0.0.1:8000/ws"
                );


            state.websocket.binaryType =
                "arraybuffer";


            // ==========================
            // OPEN
            // ==========================

            state.websocket.onopen =
                () => {

                    console.log(
                        " WebSocket connected"
                    );

                    resolve();
                };


            // ==========================
            // MESSAGE
            // ==========================

            state.websocket.onmessage =
                async (event) => {

                    // JSON
                    if (
                        typeof event.data ===
                        "string"
                    ) {

                        const message =
                            JSON.parse(
                                event.data
                            );

                        handleMessage(
                            message
                        );

                        return;
                    }


                    // Binary WAV
                    enqueueAudio(
                        event.data
                    );
                };


            // ==========================
            // ERROR
            // ==========================

            state.websocket.onerror =
                (error) => {

                    console.error(
                        " WebSocket error:",
                        error
                    );

                    setStatus(
                        "Connection error"
                    );

                    reject(error);
                };


            // ==========================
            // CLOSE
            // ==========================

            state.websocket.onclose =
                () => {

                    console.log(
                        " WebSocket closed"
                    );

                    stopAssistantAudio();

                    setStatus(
                        "Disconnected"
                    );
                };
        }
    );
}


export function sendAudio(buffer) {

    if (
        !state.websocket ||
        state.websocket.readyState !==
        WebSocket.OPEN
    ) {
        return;
    }


    state.websocket.send(buffer);
}


function handleMessage(message) {

    console.log(
        " SERVER:",
        message
    );


    switch (message.type) {


        // ==========================
        // INTERRUPT
        // ==========================

        case "interrupt":

            console.log(
                " INTERRUPT",
                message.generation
            );

            stopAssistantAudio();

            setListening();

            break;


        // ==========================
        // SPEECH START
        // ==========================

        case "speech_start":

            console.log(
                "SPEECH START"
            );

            stopAssistantAudio();

            setListening();

            break;


        // ==========================
        // PROCESSING
        // ==========================

        case "processing":

            setProcessing();


            if (
                message.stage === "stt"
            ) {

                setStatus(
                    "Understanding..."
                );

            } else if (
                message.stage === "llm"
            ) {

                setStatus(
                    "Thinking..."
                );

            } else {

                setStatus(
                    "Preparing response..."
                );
            }

            break;


        // ==========================
        // TRANSCRIPT
        // ==========================

        case "transcript":

            addMessage(
                "You",
                message.text
            );

            break;


        // ==========================
        // RESPONSE
        // ==========================

        case "response_chunk":
            addMessage(
                "Assistant",
                message.text
            );
            
            break;


        // ==========================
        // DONE
        // ==========================

        case "done":

            setListening();

            break;


        // ==========================
        // EMPTY
        // ==========================

        case "empty":

            setListening();

            break;


        // ==========================
        // ERROR
        // ==========================

        case "error":

            console.error(
                "Server error:",
                message.message
            );

            setStatus(
                "Error: " +
                message.message
            );

            break;
    }
}