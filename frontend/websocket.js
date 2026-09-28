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


export function connectWebSocket(endpoint) {

    return new Promise((resolve, reject) => {

        console.log("Connecting WebSocket...");

        // Convert HTTP endpoint to WebSocket endpoint
        const wsEndpoint =
            endpoint
                .replace(/^https:\/\//, "wss://")
                .replace(/^http:\/\//, "ws://")
                .replace(/\/$/, "");

        const wsUrl = `${wsEndpoint}/ws`;

        console.log("Connecting to:", wsUrl);

        state.websocket = new WebSocket(wsUrl);

        state.websocket.binaryType = "arraybuffer";


        // ==========================
        // OPEN
        // ==========================

        state.websocket.onopen = () => {

            console.log("WebSocket connected");

            resolve();
        };


        // ==========================
        // MESSAGE
        // ==========================

        state.websocket.onmessage = async (event) => {

            // JSON message
            if (typeof event.data === "string") {

                try {

                    const message = JSON.parse(event.data);

                    handleMessage(message);

                } catch (error) {

                    console.error(
                        "Invalid JSON from server:",
                        event.data,
                        error
                    );
                }

                return;
            }


            // Binary audio from server
            console.log(
                "Received audio:",
                event.data.byteLength,
                "bytes"
            );

            enqueueAudio(event.data);
        };


        // ==========================
        // ERROR
        // ==========================

        state.websocket.onerror = (error) => {

            console.error(
                "WebSocket error:",
                error
            );

            setStatus("Connection error");

            reject(error);
        };


        // ==========================
        // CLOSE
        // ==========================

        state.websocket.onclose = () => {

            console.log("WebSocket closed");

            stopAssistantAudio();

            setStatus("Disconnected");
        };
    });
}


export function sendAudio(buffer) {

    if (
        !state.websocket ||
        state.websocket.readyState !== WebSocket.OPEN
    ) {
        console.warn("WebSocket not open - audio not sent");
        return;
    }

    console.log(
        "Sending audio:",
        buffer.byteLength,
        "bytes"
    );

    state.websocket.send(buffer);
}


function handleMessage(message) {

    console.log("SERVER:", message);


    switch (message.type) {


        // ==========================
        // INTERRUPT
        // ==========================

        case "interrupt":

            console.log(
                "INTERRUPT",
                message.generation
            );

            stopAssistantAudio();

            setListening();

            break;


        // ==========================
        // SPEECH START
        // ==========================

        case "speech_start":

            console.log("SPEECH START");

            stopAssistantAudio();

            setListening();

            break;


        // ==========================
        // PROCESSING
        // ==========================

        case "processing":

            setProcessing();

            if (message.stage === "stt") {

                setStatus("Understanding...");

            } else if (message.stage === "llm") {

                setStatus("Thinking...");

            } else {

                setStatus("Preparing response...");
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