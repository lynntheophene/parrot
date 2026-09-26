import { state } from "./state.js";


export async function startMicrophone(sendAudio) {

    console.log(
        "Starting microphone..."
    );


    const stream =
        await navigator
            .mediaDevices
            .getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000
                }
            });


    state.audioContext =
        new AudioContext({
            sampleRate: 16000
        });


    state.microphone =
        state.audioContext
            .createMediaStreamSource(
                stream
            );


    state.processor =
        state.audioContext
            .createScriptProcessor(
                1024,
                1,
                1
            );


    state.processor.onaudioprocess =
        (event) => {

            if (
                !state.websocket ||
                state.websocket.readyState !==
                WebSocket.OPEN
            ) {
                return;
            }


            const input =
                event
                    .inputBuffer
                    .getChannelData(0);


            const buffer =
                new Float32Array(input);


            sendAudio(
                buffer.buffer
            );
        };


    state.microphone.connect(
        state.processor
    );


    state.processor.connect(
        state.audioContext.destination
    );


    console.log(
        " Microphone ready"
    );
}


export function stopMicrophone() {

    if (state.processor) {

        state.processor.disconnect();

        state.processor = null;
    }


    if (state.microphone) {

        state.microphone.disconnect();

        state.microphone = null;
    }


    if (state.audioContext) {

        state.audioContext.close();

        state.audioContext = null;
    }
}