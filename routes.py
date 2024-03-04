from flask import flash, render_template, redirect, request, session, url_for
from flask_socketio import join_room, leave_room, rooms, send
from functools import wraps
from sqlalchemy import text
from utils import generate_room_code,login_required
from main import app, socketio , db
from werkzeug.security import generate_password_hash, check_password_hash
from models import  User , Room , Message , Join

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
    
    if not all(request.form.values()):
        return render_template("error.html", message="All fields are required.")
    ## assign to variables
    if request.form.get("password1") != request.form.get("password2"):
        return render_template("error.html", message="Passwords do not match.")
        
        
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    email = request.form.get("email")
    password = request.form.get("password1")
    
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('Email already exists. Please use a different email.', 'error')
        return render_template("register.html")

    new_user = User(first_name=first_name, last_name=last_name, email=email)
    new_user.set_password(password)
    
    db.session.add(new_user)
    db.session.commit()
    flash('Đăng ký thành công, bạn có thể đăng nhập ngay bây giờ.', 'success')
    
    return redirect(url_for('home'))

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['first_name'] = user.first_name
            session["email"] = user.email
            session["logged_in"] = True
            flash('Logged in successfully.', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('index'))
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash('You were successfully logged out')
    return redirect(url_for("index"))

@app.route('/home', methods=["GET", "POST"])
def home():
    if request.method != "POST":
        return render_template('home.html')
    name = request.form.get('name')
    code = request.form.get('code')
    join = request.form.get('join', False)
    create = request.form.get('create', False)

    if not name:
        return render_template('home.html', error="Name is required", code=code)

    if create != False:
        new_code = generate_room_code(6, [room.code for room in Room.query.all()])
        room = Room(code=new_code)
        db.session.add(room)
        db.session.commit()
        flash('Room created successfully.', 'success')
        return redirect(url_for('room', room_code=new_code))

    if join != False:
        if not code:
            return render_template('home.html', error="Please enter a room code to enter a chat room", name=name)

        if "user_id" not in session:
            flash('You need to login to join a room.', 'error')
            return redirect(url_for('login'))
        if room := Room.query.filter_by(code=code).first():
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
    room_code = session.get('room')
    name = session.get('name')

    if name is None or room is None:
        return redirect(url_for('home'))

    # Check if room exists in the database
    room = Room.query.filter_by(code=room_code).first()

    if room is None:
        return redirect(url_for('home'))

    messages = Message.query.filter_by(room_id=room.id).all()
    return render_template('room.html', room=room_code, user=name, messages=messages)


@socketio.on('connect')
def handle_connect():
    room_code = session.get('room')
    name = session.get('name')

    if name is None or room_code is None:
        return
    if room_code not in rooms:
        leave_room(room_code)

    join_room(room_code)
    send({
        "sender": "",
        "message": f"{name} has entered the chat"
    }, to=room_code)
    rooms[room_code]["members"] += 1


@socketio.on('message')
def handle_message(payload):
    room_code = session.get('room')
    name = session.get('name')

    if not room_code:
        print("No room code found in session")
        return

    message_content = payload.get("message")
    if message_content:
        room = Room.query.filter_by(code=room_code).first()
        if room :
            message = Message(content=message_content, room_id=room.id)
            db.session.add(message)
            db.session.commit()

            message_data = {
                "sender": name,
                "message": f"{name} has entered the chat"
            }
            send(message_data, to=room_code)
        else:
            print(f"Room with code {room_code} does not exist")
    else:
        print("Empty message content received from client")


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