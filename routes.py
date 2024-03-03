from flask import flash, render_template, redirect, request, session, url_for
from flask_socketio import join_room, leave_room, rooms, send
from functools import wraps
from sqlalchemy import text
from utils import generate_room_code,login_required
from main import app, socketio , db
from models import db, User , Room

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("email") is None:
            flash("You need to login to access this page." , "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
        return render_template('index.html')



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    #if form values are empty show error
    if not request.form.get("first_name"):
        return render_template("error.html", message="Must provide First Name")
    elif not request.form.get("last_name"):
        return render_template("error.html", message="Must provide Last Name")
    elif  not request.form.get("email"):
        return render_template("error.html", message="Must provide E-mail")
    elif not request.form.get("password1") or not request.form.get("password2"):
        return render_template("error.html", message="Must provide password")
    elif request.form.get("password1") != request.form.get("password2"):
        return render_template("error.html", message="Password does not match")
    else :
        ## assign to variables
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password1")
        # try to commit to database, raise error if any
    
        #success - redirect to login
        new_user = User(first_name=first_name, last_name=last_name, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Đăng ký thành công, bạn có thể đăng nhập ngay bây giờ.', 'success')
        
        return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method != "POST":
        return render_template("login.html")
    form_email = request.form.get("email")
    form_password = request.form.get("password")
    # Ensure username and password was submitted
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        session['user_id'] = user.id
        flash('Đăng nhập thành công.', 'success')
        return redirect(url_for('index'))
    else:
        flash('Email hoặc mật khẩu không đúng.', 'danger')
        return redirect(url_for('login'))


@app.route("/logout")
@login_required
def logout():
    # Forget any user_id
    session.clear()
    flash('You were successfully logged out')
    # Redirect user to login index
    return redirect(url_for("index"))

@app.route('/home', methods=["GET", "POST"])
def home():
    
    if request.method != "POST":
        return render_template('home.html', code = "")
    
    name = request.form.get('name')
    code = request.form.get('code')
    join = request.form.get('join', False)
    create = request.form.get('create', False)

    if not name:
        return render_template('home.html', error="Name is required", code=code)

    if create:
        # Tạo mã phòng mới và thêm vào cơ sở dữ liệu
        room = Room(name=code)  # Assuming 'code' is the room name
        db.session.add(room)
        db.session.commit()
        flash('Room created successfully.', 'success')

    if join:
        if not code:
            return render_template('home.html', error="Please enter a room code to enter a chat room", name=name)
        
        # Kiểm tra xem phòng có tồn tại trong cơ sở dữ liệu hay không
        room = Room.query.filter_by(code=code).first()
        if room:
            # Tạo một bản ghi mới cho người dùng trong phòng
            # (Giả sử bạn có một bảng tham gia để lưu thông tin người dùng tham gia vào phòng)
            new_join = Join(user_id=session.get("user_id"), room_id=room.id)
            db.session.add(new_join)
            db.session.commit()
            flash('Joined room successfully.', 'success')
        else:
            flash('Room does not exist.', 'error')

    # Redirect đến route chat room với mã phòng đã nhập
    return redirect(url_for('room', room_code=code))
    



@app.route('/room')
def room():
    room = session.get('room')
    name = session.get('name')

    if name is None or room is None:
        return redirect(url_for('home'))

    # Check if room exists in the database
    db_room = db.execute(
        text("SELECT * FROM rooms WHERE room_code = :room_code"),
        {"room_code": room}
    ).fetchone()

    if db_room is None:
        return redirect(url_for('home'))

    messages = rooms.get(room, {}).get('messages', [])
    return render_template('room.html', room=room, user=name, messages=messages)


@socketio.on('connect')
def handle_connect():
    room = session.get('room')
    name = session.get('name')

    if name is None or room is None:
        return
    if room not in rooms:
        leave_room(room)

    join_room(room)
    send({
        "sender": "",
        "message": f"{name} has entered the chat"
    }, to=room)
    rooms[room]["members"] += 1


@socketio.on('message')
def handle_message(payload):
    room = session.get('room')
    name = session.get('name')

    if room not in rooms:
        return

    message = {
        "sender": name,
        "message": payload["message"]
    }
    send(message, to=room)
    rooms[room]["messages"].append(message)

    try:
        db.execute(text("UPDATE rooms SET messages = :messages WHERE room_code = :room_code"),
                {"messages": rooms[room]["messages"], "room_code": room})
        db.commit()
    except Exception as e:
        print("Error updating messages to database:", e)


@socketio.on('disconnect')
def handle_disconnect():
    room = session.get("room")
    name = session.get("name")

    if room in rooms:
        leave_room(room)
        rooms[room]["members"] -= 1

        # Kiểm tra xem có ai còn trong phòng không
        if rooms[room]["members"] <= 0:
            del rooms[room]

            # Xóa phòng ra khỏi cơ sở dữ liệu khi không còn ai trong phòng
            try:
                db.execute(text("DELETE FROM rooms WHERE room_code = :room_code"),
                        {"room_code": room})
                db.commit()
                print("Room deleted from database:", room)
            except Exception as e:
                print("Error deleting room from database:", e)
        else:
            print("Room still has members:", room)

    else:
        print("Room not found in rooms:", room)