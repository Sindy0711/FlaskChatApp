# Import các module cần thiết
from flask import flash, render_template, redirect, request, session, url_for
from flask_socketio import join_room, leave_room, rooms, send
from functools import wraps
from sqlalchemy import text
from utils import generate_room_code,login_required  # import các hàm tiện ích từ module utils
from main import app, socketio , db  # import các biến và function từ module main
from werkzeug.security import generate_password_hash, check_password_hash  # Import các hàm mã hóa và kiểm tra mật khẩu từ Werkzeug
from models import  User , Room , Message , Join  # import các model từ module models

# Decorator để kiểm tra đăng nhập
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("email") is None:
            flash("You need to login to access this page." , "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# Route chính, hiển thị trang index
@app.route('/')
def index():
        session.clear()  # Xóa các session hiện tại
        return render_template('index.html')  # Trả về template index.html

# Route xử lý đăng ký
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")  # Trả về template register.html khi request là GET
    
    if not all(request.form.values()):  # Kiểm tra nếu không có giá trị nào trong form
        return render_template("error.html", message="All fields are required.")  # Trả về template error.html

    if request.form.get("password1") != request.form.get("password2"):  # Kiểm tra xác nhận mật khẩu
        return render_template("error.html", message="Passwords do not match.")  # Trả về template error.html

    # Gán giá trị từ form vào các biến
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    email = request.form.get("email")
    password = request.form.get("password1")
    
    existing_user = User.query.filter_by(email=email).first()  # Kiểm tra xem người dùng đã tồn tại chưa
    if existing_user:
        flash('Email already exists. Please use a different email.', 'error')  # Thông báo nếu email đã tồn tại
        return render_template("register.html")  # Trả về template register.html

    # Tạo người dùng mới
    new_user = User(first_name=first_name, last_name=last_name, email=email)
    new_user.set_password(password)  # Mã hóa mật khẩu
    db.session.add(new_user)  # Thêm người dùng vào cơ sở dữ liệu
    db.session.commit()  # Lưu thay đổi
    flash('Đăng ký thành công, bạn có thể đăng nhập ngay bây giờ.', 'success')  # Thông báo đăng ký thành công
    
    return redirect(url_for('home'))  # Chuyển hướng đến trang home

# Route xử lý đăng nhập
@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()  # Xóa các session hiện tại
    if request.method == "POST":
        
        email = request.form.get("email")  # Lấy email từ form
        password = request.form.get("password")  # Lấy mật khẩu từ form
        
        user = User.query.filter_by(email=email).first()  # Tìm người dùng theo email
        if user is None:
            flash('User does not exist. Please check your email.', 'danger')  # Thông báo nếu người dùng không tồn tại
            return redirect(url_for('index'))  # Chuyển hướng đến trang index

        if user and check_password_hash(user.password, password):  # Kiểm tra mật khẩu
            session['user_id'] = user.id
            session['first_name'] = user.first_name
            session["email"] = user.email
            session["logged_in"] = True
            flash('Logged in successfully.', 'success')  # Thông báo đăng nhập thành công
            return redirect(url_for('home'))  # Chuyển hướng đến trang home
        else:
            flash('Invalid email or password.', 'danger')  # Thông báo nếu email hoặc mật khẩu không hợp lệ
            return redirect(url_for('index'))  # Chuyển hướng đến trang index
    return render_template("login.html")  # Trả về template login.html khi request là GET

# Route xử lý đăng xuất
@app.route("/logout")
@login_required
def logout():
    session.clear()  # Xóa các session hiện tại
    flash('You were successfully logged out')  # Thông báo đăng xuất thành công
    return redirect(url_for("index"))  # Chuyển hướng đến trang index

# Route xử lý trang chính
@app.route('/home', methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get('name')  # Lấy tên từ form
        create = request.form.get('create', False)  # Lấy giá trị tạo phòng từ form
        code = request.form.get('code')  # Lấy mã phòng từ form
        join = request.form.get('join', False)  # Lấy giá trị tham gia phòng từ form

        if not name:  # Kiểm tra nếu không có tên
            return render_template('home.html', error="Name is required", code=code)  # Trả về template home.html với thông báo lỗi

        if create != False:  # Nếu yêu cầu tạo phòng
            room_code = generate_room_code(6, [room.code for room in Room.query.all()])  # Tạo mã phòng mới
            room = Room(code=room_code)  # Tạo đối tượng phòng mới
            db.session.add(room)  # Thêm phòng vào cơ sở dữ liệu
            db.session.commit()  # Lưu thay đổi
            flash('Room created successfully.', 'success')  # Thông báo tạo phòng thành công
            session['room'] = room_code  # Lưu mã phòng vào session
            session['name'] = name  # Lưu tên vào session
            return redirect(url_for('room'))  # Chuyển hướng đến trang room

        if join != False:  # Nếu yêu cầu tham gia phòng
            if not code:  # Kiểm tra nếu không có mã phòng
                return render_template('home.html', error="Please enter a room code to enter a chat room", name=name)  # Trả về template home.html với thông báo lỗi

            room = Room.query.filter_by(code=code).first()  # Tìm phòng theo mã
            if room:
                # Kiểm tra xem người dùng đã ở trong phòng chưa
                user_in_room = Join.query.filter_by(user_id=session.get("user_id"), room_id=room.id).first()
                if not user_in_room:
                    current_room_code = session.get('room')
                    if current_room_code:
                        current_room = Room.query.filter_by(code=current_room_code).first()
                        if current_room:
                            # Xóa người dùng khỏi phòng hiện tại
                            join_to_delete = Join.query.filter_by(user_id=session.get("user_id"), room_id=current_room.id).first()
                            if join_to_delete:
                                db.session.delete(join_to_delete)
                                db.session.commit()
                                
                    new_join = Join(user_id=session.get("user_id"), room_id=room.id)  # Tạo bản ghi tham gia mới
                    db.session.add(new_join)  # Thêm vào cơ sở dữ liệu
                    db.session.commit()  # Lưu thay đổi
                    flash('Joined room successfully.', 'success')  # Thông báo tham gia phòng thành công
                    session['room'] = code  # Lưu mã phòng vào session
                    session['name'] = name  # Lưu tên vào session
                    return redirect(url_for('room'))  # Chuyển hướng đến trang room
                else:
                    flash('You are already in this room.', 'error')  # Thông báo nếu người dùng đã ở trong phòng
            else:
                flash('Room does not exist.', 'error')  # Thông báo nếu phòng không tồn tại

    rooms = Room.query.all()  # Lấy danh sách các phòng
    return render_template('home.html', rooms=rooms)  # Trả về template home.html với danh sách các phòng

# Route xử lý trang phòng
@app.route('/room')
def room():
    room_code = session.get('room')  # Lấy mã phòng từ session
    name = session.get('name')  # Lấy tên từ session

    if name is None or room_code is None:  # Kiểm tra xem có tên và mã phòng không
        return redirect(url_for('home'))  # Chuyển hướng đến trang home

    # Kiểm tra xem phòng có tồn tại trong cơ sở dữ liệu không
    room = Room.query.filter_by(code=room_code).first()

    if room_code is None:  # Nếu không có mã phòng
        return redirect(url_for('home'))  # Chuyển hướng đến trang home

    messages = Message.query.filter_by(room_id=room.id).all()  # Lấy danh sách tin nhắn trong phòng
    return render_template('room.html', room=room_code, user=name, messages=messages)  # Trả về template room.html với thông tin phòng và tin nhắn

# Xử lý khi có kết nối từ client
@socketio.on('connect')
def handle_connect():
    room_code = session.get('room')  # Lấy mã phòng từ session
    name = session.get('first_name')  # Lấy tên từ session

    if name is None or room_code is None:  # Kiểm tra xem có tên và mã phòng không
        return
    
    room = Room.query.filter_by(code=room_code).first()  # Tìm phòng trong cơ sở dữ liệu
    
    if room is None:  # Nếu không tìm thấy phòng
        flash('Room does not exist.', 'error')  # Thông báo phòng không tồn tại
        return

    user = User.query.filter_by(first_name=name).first()  # Tìm người dùng trong cơ sở dữ liệu
    if user:
        join_record = Join.query.filter_by(user_id=user.id, room_id=room.id).first()  # Kiểm tra bản ghi tham gia
        if not join_record:  # Nếu không có bản ghi tham gia
            new_join = Join(user_id=user.id, room_id=room.id)  # Tạo bản ghi tham gia mới
            db.session.add(new_join)  # Thêm vào cơ sở dữ liệu
            db.session.commit()  # Lưu thay đổi

    join_room(room_code)  # Tham gia vào phòng
    send({
        "sender": "",
        "message": f"{name} has entered the chat"
    }, to=room_code)  # Gửi tin nhắn nhập phòng
    
    num_members = Join.query.filter_by(room_id=room.id).count()  # Đếm số thành viên trong phòng
    room.members = num_members  # Cập nhật số thành viên
    db.session.commit()  # Lưu thay đổi

# Xử lý khi có tin nhắn từ client
@socketio.on('message')
def handle_message(payload):
    room_code = session.get('room')  # Lấy mã phòng từ session
    name = session.get('name')  # Lấy tên từ session

    if not room_code:  # Nếu không có mã phòng
        print("No room code found in session")  # In thông báo lỗi
        return

    message_content = payload.get("message")  # Lấy nội dung tin nhắn
    if message_content:  # Nếu có nội dung tin nhắn
        room = Room.query.filter_by(code=room_code).first()  # Tìm phòng trong cơ sở dữ liệu
        if room:
            message = Message(content=message_content, room_id=room.id)  # Tạo đối tượng tin nhắn mới
            db.session.add(message)  # Thêm vào cơ sở dữ liệu
            db.session.commit()  # Lưu thay đổi

            message_data = {
                "sender": name,
                "message": message_content
            }
            send(message_data, to=room_code)  # Gửi tin nhắn đến các thành viên trong phòng
        else:
            print(f"Room with code {room_code} does not exist")  # In thông báo lỗi nếu không tìm thấy phòng
    else:
        print("Empty message content received from client")  # In thông báo lỗi nếu không có nội dung tin nhắn

# Xử lý khi client ngắt kết nối
@socketio.on('disconnect')
def handle_disconnect():
    room_code = session.get('room')  # Lấy mã phòng từ session
    name = session.get('name')  # Lấy tên từ session

    room = Room.query.filter_by(code=room_code).first()  # Tìm phòng trong cơ sở dữ liệu
    
    if room:  # Nếu tìm thấy phòng
        user = User.query.filter_by(first_name=name).first()  # Tìm người dùng trong cơ sở dữ liệu
        if user:
            join_record = Join.query.filter_by(user_id=user.id, room_id=room.id).first()  # Kiểm tra bản ghi tham gia
            if join_record:  # Nếu có bản ghi tham gia
                try:
                    db.session.delete(join_record)  # Xóa bản ghi tham gia
                    db.session.commit()  # Lưu thay đổi
                    print("User left room:", name)  # In thông báo
                except Exception as e:
                    print("Error deleting user from room:", e)  # In thông báo lỗi khi xóa bản ghi tham gia
        
        num_members = Join.query.filter_by(room_id=room.id).count()  # Đếm số thành viên trong phòng
        if num_members <= 0:  # Nếu không còn thành viên trong phòng
            try:
                Message.query.filter_by(room_id=room.id).delete()  # Xóa các tin nhắn trong phòng
                db.session.delete(room)  # Xóa phòng
                db.session.commit()  # Lưu thay đổi
                print("Room deleted from database:", room_code)  # In thông báo
            except Exception as e:
                print("Error deleting room from database:", e)  # In thông báo lỗi khi xóa phòng
        else:
            print("Room still has members:", room_code)  # In thông báo nếu phòng còn thành viên
    else:
        flash('Room does not exist.', 'error')  # Thông báo nếu không tìm thấy phòng
    flash('You were successfully logged out')  # Thông báo đăng xuất thành công
    session.clear()
    return redirect(url_for('home'))  # Chuyển hướng đến trang home
