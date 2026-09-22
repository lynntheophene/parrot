import { state } from "./state.js";

import {
    setStatus,
    disableStartButton,
    startOrb
} from "./ui.js";

import {
    connectWebSocket,
    sendAudio
} from "./websocket.js";

import {
    startMicrophone
} from "./microphone.js";


const startButton =
    document.getElementById(
        "startButton"
    );


async function startConversation() {

    console.log(
        " Starting voice assistant..."
    );


    setStatus(
        "Requesting microphone..."
    );


    try {

        // ==========================
        // WEBSOCKET
        // ==========================

        await connectWebSocket();


        // ==========================
        // MICROPHONE
        // ==========================

        await startMicrophone(
            sendAudio
        );


        state.started = true;


        disableStartButton();

        startOrb();


        setStatus(
            "Connected — speak normally"
        );


        console.log(
            " Voice assistant ready"
        );


    } catch (error) {

        console.error(
            " Failed to start assistant:",
            error
        );


        setStatus(
            "Failed to start"
        );
    }
}


startButton.onclick =
    startConversation;