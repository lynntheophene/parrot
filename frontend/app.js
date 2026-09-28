import { state } from "./state.js";

import {
    setStatus,
    disableStartButton,
    startOrb
} from "./ui.js";

import {
    connectWebSocket,
    sendAudio
} from "./websocket.js?v=3";

import {
    startMicrophone
} from "./microphone.js";


const startButton =
    document.getElementById("startButton");

const stopButton =
    document.getElementById("stopButton");


const CONTROL_API =
    "https://parrot-worker.parrot-control.workers.dev";


// ========================================
// START
// ========================================

async function startConversation() {

    console.log("Starting voice assistant...");

    setStatus("Starting Parrot...");

    try {

        // ==========================
        // START CLOUD INSTANCE
        // ==========================

        console.log(
            "Requesting Parrot instance..."
        );

        const response =
            await fetch(
                `${CONTROL_API}/start`,
                {
                    method: "POST"
                }
            );

        if (!response.ok) {

            throw new Error(
                `Start request failed: ${response.status}`
            );
        }

        const data =
            await response.json();

        console.log(
            "Start response:",
            data
        );

        if (
            !data.ready ||
            !data.endpoint
        ) {

            throw new Error(
                "Parrot backend is not ready"
            );
        }

        const endpoint =
            data.endpoint;

        console.log(
            "Parrot endpoint:",
            endpoint
        );


        // ==========================
        // WEBSOCKET
        // ==========================

        setStatus(
            "Connecting to Parrot..."
        );

        await connectWebSocket(
            endpoint
        );


        // ==========================
        // MICROPHONE
        // ==========================

        setStatus(
            "Starting microphone..."
        );

        await startMicrophone(
            sendAudio
        );


        // ==========================
        // UI
        // ==========================

        state.started = true;

        startButton.disabled = true;
        stopButton.disabled = false;

        startOrb();

        setStatus(
            "Connected — speak normally"
        );

        console.log(
            "Voice assistant ready"
        );


    } catch (error) {

        console.error(
            "Failed to start assistant:",
            error
        );

        setStatus(
            "Failed to start: " +
            error.message
        );

        startButton.disabled = false;
        stopButton.disabled = true;
    }
}


// ========================================
// STOP
// ========================================

async function stopConversation() {

    console.log(
        "Stopping Parrot..."
    );

    setStatus(
        "Stopping Parrot..."
    );


    try {

        // ==========================
        // CLOSE WEBSOCKET
        // ==========================

        if (state.websocket) {

            console.log(
                "Closing WebSocket..."
            );

            state.websocket.close();

            state.websocket = null;
        }


        // ==========================
        // STOP CLOUD INSTANCE
        // ==========================

        console.log(
            "Requesting Parrot shutdown..."
        );

        const response =
            await fetch(
                `${CONTROL_API}/stop`,
                {
                    method: "POST"
                }
            );


        if (!response.ok) {

            throw new Error(
                `Stop request failed: ${response.status}`
            );
        }


        const data =
            await response.json();


        console.log(
            "Stop response:",
            data
        );


        // ==========================
        // STATE
        // ==========================

        state.started = false;

        startButton.disabled = false;
        stopButton.disabled = true;


        setStatus(
            "Parrot stopped"
        );


        console.log(
            "Parrot stopped"
        );


    } catch (error) {

        console.error(
            "Failed to stop Parrot:",
            error
        );

        setStatus(
            "Failed to stop: " +
            error.message
        );
    }
}


// ========================================
// BUTTONS
// ========================================

startButton.onclick =
    startConversation;

stopButton.onclick =
    stopConversation;


// Initial state

stopButton.disabled = true;