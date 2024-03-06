var socketio = io(); // Khởi tạo kết nối socketio

// Thiết lập sự kiện trước khi cửa sổ trình duyệt được xóa
window.onbeforeunload = function () {
  // Tạo một kết nối socketio mới
  var socket = io.connect('http://' + document.domain + ':' + location.port);

  // Lấy mã phòng và tên người dùng từ session
  var roomCode = "{{ session.get('room') }}";
  var userName = "{{ session.get('name') }}";

  // Kiểm tra nếu có mã phòng và tên người dùng
  if (roomCode && userName) {
    // Gửi sự kiện 'disconnect' với dữ liệu là mã phòng và tên người dùng
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
