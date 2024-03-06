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
        session.clear()
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
        if user is None:
            flash('User does not exist. Please check your email.', 'danger')
            return redirect(url_for('index'))

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
    if request.method == "POST":
        name = request.form.get('name')
        create = request.form.get('create', False)
        code = request.form.get('code')
        join = request.form.get('join', False)

        if not name:
            return render_template('home.html', error="Name is required", code=code)

        if create != False:
            room_code = generate_room_code(6, [room.code for room in Room.query.all()])
            room = Room(code=room_code)
            db.session.add(room)
            db.session.commit()
            flash('Room created successfully.', 'success')
            session['room'] = room_code
            session['name'] = name
            return redirect(url_for('room'))

        if join != False:
            if not code:
                return render_template('home.html', error="Please enter a room code to enter a chat room", name=name)

            room = Room.query.filter_by(code=code).first()
            if room:
                # Check if the user is already in the room
                user_in_room = Join.query.filter_by(user_id=session.get("user_id"), room_id=room.id).first()
                if not user_in_room:
                    current_room_code = session.get('room')
                    if current_room_code:
                        current_room = Room.query.filter_by(code=current_room_code).first()
                        if current_room:
                            # Xóa người dùng khỏi phòng cũ
                            join_to_delete = Join.query.filter_by(user_id=session.get("user_id"), room_id=current_room.id).first()
                            if join_to_delete:
                                db.session.delete(join_to_delete)
                                db.session.commit()
                                
                    new_join = Join(user_id=session.get("user_id"), room_id=room.id)
                    db.session.add(new_join)
                    db.session.commit()
                    flash('Joined room successfully.', 'success')
                    session['room'] = code
                    session['name'] = name
                    return redirect(url_for('room'))
                else:
                    flash('You are already in this room.', 'error')
            else:
                flash('Room does not exist.', 'error')

    rooms = Room.query.all()
    return render_template('home.html', rooms=rooms)




@app.route('/room')
def room():
    room_code = session.get('room')
    name = session.get('name')

    if name is None or room_code is None:
        return redirect(url_for('home'))

    # Check if room exists in the database
    room = Room.query.filter_by(code=room_code).first()

    if room_code is None:
        return redirect(url_for('home'))

    messages = Message.query.filter_by(room_id=room.id).all()
    return render_template('room.html', room=room_code, user=name, messages=messages)


@socketio.on('connect')
def handle_connect():
    room_code = session.get('room')
    name = session.get('first_name')

    if name is None or room_code is None:
        return
    
    room = Room.query.filter_by(code=room_code).first()
    
    if room is None:
        flash('Room does not exist.', 'error')
        return

    user = User.query.filter_by(first_name=name).first()
    if user:
        join_record = Join.query.filter_by(user_id=user.id, room_id=room.id).first()
        if not join_record:
            new_join = Join(user_id=user.id, room_id=room.id)
            db.session.add(new_join)
            db.session.commit()

    join_room(room_code)
    send({
        "sender": "",
        "message": f"{name} has entered the chat"
    }, to=room_code)
    
    num_members = Join.query.filter_by(room_id=room.id).count()
    room.members = num_members
    db.session.commit()


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
        if room:
            message = Message(content=message_content, room_id=room.id)
            db.session.add(message)
            db.session.commit()

            message_data = {
                "sender": name,
                "message": message_content
            }
            send(message_data, to=room_code)
        else:
            print(f"Room with code {room_code} does not exist")
    else:
        print("Empty message content received from client")


@socketio.on('disconnect')
def handle_disconnect():
    room_code = session.get('room')
    name = session.get('name')

    room = Room.query.filter_by(code=room_code).first()
    
    if room:
        user = User.query.filter_by(first_name=name).first()
        if user:
            join_record = Join.query.filter_by(user_id=user.id, room_id=room.id).first()
            if join_record:
                try:
                    db.session.delete(join_record)
                    db.session.commit()
                    print("User left room:", name)
                except Exception as e:
                    print("Error deleting user from room:", e)
        
        # Kiểm tra xem còn ai trong phòng không
        num_members = Join.query.filter_by(room_id=room.id).count()
        if num_members <= 0:
            try:
                Message.query.filter_by(room_id=room.id).delete()
                db.session.delete(room)
                db.session.commit()
                print("Room deleted from database:", room_code)
            except Exception as e:
                print("Error deleting room from database:", e)
        else:
            print("Room still has members:", room_code)
    else:
        flash('Room does not exist.', 'error')
    flash('You were successfully logged out')
        
    return redirect(url_for('home'))
