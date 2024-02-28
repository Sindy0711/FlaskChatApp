document.addEventListener("DOMContentLoaded", function () {
    const socketio = io();

    socketio.on("message", function (message) {
        createChatItem(message.message, message.sender);
    });

    function createChatItem(message, sender) {
        const messages = document.getElementById("messages");
        let content = ``;

        if (sender === "") {
            content = `<p class="member-activity">${message}</p>`;
        } else {
            const senderIsUser = currentUser === sender;
            const messageClass = senderIsUser ? "self-message-item" : "peer-message-item";
            const mutedTextClass = senderIsUser ? "muted-text" : "muted-text-white";

            content = `
                <li class="message-item ${messageClass}">
                    <p>${message}</p>
                    <small class="${mutedTextClass}">${new Date().toLocaleString()}</small>
                </li>
            `;
        }

        messages.innerHTML += content;
    }

    function sendMessage() {
        const msgInput = document.getElementById("message-input");
        const msg = msgInput.value;
        if (msg !== "") {
            if (socketio.connected) {
                socketio.emit("message", { message: msg });
            } else {
                console.error("Socket is not connected.");
            }
            msgInput.value = "";
        }
    }
});