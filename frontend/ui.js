const status = document.getElementById("status");
const orb = document.getElementById("orb");
const conversation = document.getElementById("conversation");
const startButton = document.getElementById("startButton");


export function setStatus(text) {
    status.textContent = text;
}


export function setListening() {

    orb.classList.remove("processing");
    orb.classList.add("listening");

    setStatus("Listening...");
}


export function setProcessing() {

    orb.classList.remove("listening");
    orb.classList.add("processing");
}


export function addMessage(label, text) {

    const message =
        document.createElement("div");

    message.className = "message";

    message.innerHTML = `
        <div class="label">
            ${label}
        </div>

        <div>
            ${text}
        </div>
    `;

    conversation.appendChild(message);
}


export function disableStartButton() {
    startButton.disabled = true;
}


export function enableStartButton() {
    startButton.disabled = false;
}


export function startOrb() {
    orb.classList.add("listening");
}


export function stopOrb() {

    orb.classList.remove("listening");
    orb.classList.remove("processing");
}