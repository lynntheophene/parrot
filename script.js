const startButton =
    document.getElementById("startButton");

const status =
    document.getElementById("status");

const orb =
    document.getElementById("orb");

const conversation =
    document.getElementById("conversation");


let websocket = null;

let audioContext = null;

let microphone = null;

let processor = null;


// ============================================
// CURRENT ASSISTANT AUDIO
// ============================================

let currentAudio = null;

let currentAudioUrl = null;

// Invalidates old assistant audio whenever the user interrupts.
let audioGeneration = 0;


// ============================================
// STATUS
// ============================================

function setStatus(text) {

    status.textContent = text;

}


// ============================================
// ADD MESSAGE
// ============================================

function addMessage(
    label,
    text
) {

    const message =
        document.createElement("div");

    message.className =
        "message";

    message.innerHTML = `
        <div class="label">
            ${label}
        </div>

        <div>
            ${text}
        </div>
    `;

    conversation.appendChild(
        message
    );

}


// ============================================
// STOP ASSISTANT AUDIO
// ============================================

function stopAssistantAudio() {

    console.log(" STOP ASSISTANT AUDIO");

    // Invalidate all existing assistant audio.
    audioGeneration++;

    if (currentAudio) {

        console.log(" Stopping current Audio object");

        try {
            currentAudio.pause();
            currentAudio.currentTime = 0;

            // Completely detach the audio source.
            currentAudio.src = "";
            currentAudio.load();

        } catch (error) {

            console.warn(
                "Audio stop warning:",
                error
            );
        }

        currentAudio.onended = null;
        currentAudio.onerror = null;

        currentAudio = null;
    }

    if (currentAudioUrl) {

        console.log(
            "Releasing audio URL"
        );

        try {

            URL.revokeObjectURL(
                currentAudioUrl
            );

        } catch (error) {

            console.warn(
                "URL cleanup warning:",
                error
            );
        }

        currentAudioUrl = null;
    }

    console.log(
        "Audio invalidated. Generation:",
        audioGeneration
    );
}


// ============================================
// START CONVERSATION
// ============================================

async function startConversation() {

    setStatus(
        "Requesting microphone..."
    );

    try {

        const stream =
            await navigator
                .mediaDevices
                .getUserMedia({

                    audio: {

                        channelCount: 1,

                        sampleRate: 16000

                    }

                });


        // ====================================
        // AUDIO CONTEXT
        // ====================================

        audioContext =
            new AudioContext({

                sampleRate: 16000

            });


        microphone =
            audioContext
                .createMediaStreamSource(
                    stream
                );


        // ====================================
        // AUDIO PROCESSOR
        // ====================================

        processor =
            audioContext
                .createScriptProcessor(
                    1024,
                    1,
                    1
                );


        // ====================================
        // WEBSOCKET
        // ====================================

        websocket =
            new WebSocket(
                "ws://127.0.0.1:8000/ws"
            );


        websocket.binaryType =
            "arraybuffer";


        // ====================================
        // WEBSOCKET OPEN
        // ====================================

        websocket.onopen = () => {

            setStatus(
                "Connected — speak normally"
            );

            startButton.disabled =
                true;

            orb.classList.add(
                "listening"
            );


            // =================================
            // SEND MICROPHONE AUDIO
            // =================================

            processor.onaudioprocess =
                (event) => {

                    if (
                        websocket.readyState
                        !== WebSocket.OPEN
                    ) {

                        return;

                    }


                    const input =
                        event
                            .inputBuffer
                            .getChannelData(0);


                    const buffer =
                        new Float32Array(
                            input
                        );


                    websocket.send(
                        buffer.buffer
                    );

                };


            microphone.connect(
                processor
            );


            processor.connect(
                audioContext.destination
            );

        };


        // ====================================
        // WEBSOCKET MESSAGE
        // ====================================

        websocket.onmessage =
            async (event) => {

                // JSON message
                if (
                    typeof event.data
                    === "string"
                ) {

                    const message =
                        JSON.parse(
                            event.data
                        );

                    handleMessage(
                        message
                    );

                }

                // Binary WAV
                else {

                    await playAudio(
                        event.data
                    );

                }

            };


        // ====================================
        // WEBSOCKET ERROR
        // ====================================

        websocket.onerror = () => {

            setStatus(
                "Connection error"
            );

        };


        // ====================================
        // WEBSOCKET CLOSE
        // ====================================

        websocket.onclose = () => {

            stopAssistantAudio();

            setStatus(
                "Disconnected"
            );

            startButton.disabled =
                false;

            orb.classList.remove(
                "listening"
            );

        };


    } catch (error) {

        console.error(
            error
        );

        setStatus(
            "Microphone permission denied"
        );

    }

}


// ============================================
// HANDLE SERVER MESSAGES
// ============================================

function handleMessage(
    message
) {

    console.log(
        message
    );


    switch (
        message.type
    ) {


        // ==================================
        // USER STARTED SPEAKING
        // ==================================

        case "interrupt":

            console.log(
                " INTERRUPT RECEIVED FROM SERVER",
                message.generation
            );

            stopAssistantAudio();

            setStatus("Listening...");

            orb.classList.remove("processing");

            orb.classList.add("listening");

            break;


        case "speech_start":

            console.log(
                " SPEECH START → INTERRUPTING ASSISTANT"
            );

            stopAssistantAudio();

            setStatus("Listening...");

            orb.classList.add("listening");

            break;


        // ==================================
        // PROCESSING
        // ==================================

        case "processing":

            orb.classList.remove(
                "listening"
            );

            orb.classList.add(
                "processing"
            );


            setStatus(

                message.stage === "stt"

                    ? "Understanding..."

                    : message.stage === "llm"

                    ? "Thinking..."

                    : "Preparing response..."

            );

            break;


        // ==================================
        // TRANSCRIPT
        // ==================================

        case "transcript":

            addMessage(
                "You",
                message.text
            );

            break;


        // ==================================
        // ASSISTANT RESPONSE
        // ==================================

        case "response":

            addMessage(
                "Assistant",
                message.text
            );

            break;


        // ==================================
        // DONE
        // ==================================

        case "done":

            orb.classList.remove(
                "processing"
            );

            orb.classList.add(
                "listening"
            );

            setStatus(
                "Listening..."
            );

            break;


        // ==================================
        // EMPTY
        // ==================================

        case "empty":

            setStatus(
                "Listening..."
            );

            break;


        // ==================================
        // ERROR
        // ==================================

        case "error":

            orb.classList.remove(
                "processing"
            );

            setStatus(
                "Error: "
                + message.message
            );

            break;

    }

}


// ============================================
// PLAY ASSISTANT AUDIO
// ============================================

async function playAudio(arrayBuffer) {

    console.log(
        " RECEIVED ASSISTANT AUDIO"
    );

    // Never allow two assistant audio objects.
    stopAssistantAudio();

    // This audio belongs to the current generation.
    const myGeneration = audioGeneration;

    try {

        const blob = new Blob(
            [arrayBuffer],
            {
                type: "audio/wav"
            }
        );

        currentAudioUrl =
            URL.createObjectURL(blob);

        currentAudio =
            new Audio(
                currentAudioUrl
            );

        currentAudio.preload = "auto";


        // ==================================
        // AUDIO FINISHED
        // ==================================

        currentAudio.onended = () => {

            console.log(
                " AUDIO FINISHED"
            );

            if (currentAudioUrl) {

                try {

                    URL.revokeObjectURL(
                        currentAudioUrl
                    );

                } catch (error) {

                    console.warn(
                        "URL cleanup warning:",
                        error
                    );
                }
            }

            currentAudio = null;
            currentAudioUrl = null;

            orb.classList.remove(
                "processing"
            );

            orb.classList.add(
                "listening"
            );

            setStatus(
                "Listening..."
            );
        };


        // ==================================
        // AUDIO ERROR
        // ==================================

        currentAudio.onerror = (error) => {

            console.error(
                " Audio playback error:",
                error
            );

            stopAssistantAudio();

            setStatus(
                "Listening..."
            );
        };


        // ==================================
        // FINAL INTERRUPTION CHECK
        // ==================================

        if (
            myGeneration !== audioGeneration
        ) {

            console.log(
                " Audio invalidated before playback"
            );

            stopAssistantAudio();

            return;
        }


        // ==================================
        // PLAY
        // ==================================

        setStatus(
            "Speaking..."
        );

        console.log(
            " PLAYING ASSISTANT AUDIO",
            "generation:",
            myGeneration
        );

        await currentAudio.play();

    } catch (error) {

        console.error(
            "Audio playback error:",
            error
        );

        stopAssistantAudio();

        setStatus(
            "Listening..."
        );
    }
}


// ============================================
// START BUTTON
// ============================================

startButton.onclick =
    startConversation;
