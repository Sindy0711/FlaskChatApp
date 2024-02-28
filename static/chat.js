var socketio = io()

socketio.on("message", function (message) {
    createChatItem(message.message, message.sender)
})

function createChatItem(message, sender) {
    var messages = document.getElementById("messages");
    var content = "";

    if (sender === '') {
        content = `
          <p class="member-activity">${message}</p>
        `
    } else {
        var senderIsUser = currentUser === sender;
        content = `
          <li class="message-item ${senderIsUser ? "self-message-item" : "peer-message-item"
            }">
              <p>${message}</p>
              <small class="${senderIsUser ? "muted-text" : "muted-text-white"
            }">${new Date().toLocaleString()}</small>
          </li>
      `;
    }


    messages.innerHTML += content;
}

function sendMessage(){
    var msgInput = document.getElementById("message-input");
    var msg = msgInput.value;
    
    if (msg === "" ) return ;

    socketio.emit("message" , {message : msg});

    msgInput.value === "";
    
}