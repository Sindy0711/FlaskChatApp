var socketio = io()

window.onbeforeunload = function () {
  var socket = io.connect('http://' + document.domain + ':' + location.port);
  var roomCode = "{{ session.get('room') }}";
  var userName = "{{ session.get('name') }}";

  if (roomCode && userName) {
    socket.emit('disconnect', { room_code: roomCode, name: userName });
  }
};

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
function sendMessage() {
  var msgInput = document.getElementById("message-input");
  var msg = msgInput.value;

  if (msg === "") return;

  socketio.emit("message", { message: msg });

  msgInput.value = "";

}

// document.querySelectorAll('#join-room').forEach(button => {
//   button.addEventListener('click', function (event) {
//     event.preventDefault(); 

//     var roomCode = button.dataset.roomCode; 

  
//     fetch('/home', {
//       method: 'POST',
//       headers: {
//         'Content-Type': 'application/json'
//       },
//       body: JSON.stringify({
//         name: '{{ session.get("name") }}', 
//         join: true, 
//         code: roomCode 
//       })
//     })
//     .then(response => {
//       if (response.ok) {
//         window.location.href = '/room'; 
//       } else {
//         console.error('Failed to join room:', response.statusText);
//       }
//     })
//     .catch(error => {
//       console.error('Error joining room:', error);
//     });
//   });
// });