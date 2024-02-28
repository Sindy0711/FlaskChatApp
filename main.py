import os
from flask import Flask, request, render_template, redirect, url_for, session , flash
from flask_session import Session
from flask_socketio import SocketIO, join_room, leave_room, send
from functools import wraps
from sqlalchemy import create_engine ,text
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

from utils import generate_room_code

from dotenv import load_dotenv
load_dotenv()



app = Flask(__name__)
app.config['SECRET_KEY'] = 'SDKFJSDFOWEIOF'
socketio = SocketIO(app)


rooms = {}

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")


app.config['SESSION_PERMANENT'] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

print(engine)

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
    ## end validation
    else :
        ## assign to variables
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password1")
        # try to commit to database, raise error if any
        try:
            db.execute(text("INSERT INTO users (firstname, lastname, email, password) VALUES (:firstname, :lastname, :email, :password)"
                        ),
                        {"firstname": first_name, "lastname": last_name, "email":email, "password": generate_password_hash(password)}        
            )
        except Exception as e:
            return render_template("error.html", message=e)

        db.commit()

        #success - redirect to login
        Q = db.execute(
            text("SELECT * FROM users WHERE email LIKE :email"),
            {"email": email},
        ).fetchone()
        print(Q.userid)
        # Remember which user has logged in
        session["user_id"] = Q.userid
        session["email"] = Q.email
        session["firstname"] = Q.firstname
        session["logged_in"] = True
        return redirect(url_for("home"))

@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    if request.method != "POST":
        return render_template("login.html")
    form_email = request.form.get("email")
    form_password = request.form.get("password")

    # Ensure username and password was submitted
    if not form_email:
        return render_template("error.html", message="must provide username")
    elif not form_password:
        return render_template("error.html", message="must provide password")

    # Query database for email and password
    Q = db.execute(text("SELECT * FROM users WHERE email LIKE :email"), {"email": form_email}).fetchone()
    db.commit()
    # User exists ?
    if Q is None:
        return render_template("error.html", message="User doesn't exists")
    # Valid password ?
    if not check_password_hash( Q.password, form_password):
        return  render_template("error.html", message = "Invalid password")

    # Remember which user has logged in
    session["user_id"] = Q.userid
    session["email"] = Q.email
    session["firstname"] = Q.firstname
    session["logged_in"] = True
    return redirect(url_for("home"))

@app.route("/logout")
@login_required
def logout():
    # Forget any user_id
    session.clear()

    # Redirect user to login index
    return redirect(url_for("index"))

@app.route('/home', methods=["GET", "POST"])
def home():
    if request.method != "POST":
        return render_template('home.html')
    name = request.form.get('name')
    code = request.form.get('code')
    join = request.form.get('join')
    create = request.form.get('create')

    if not name:
        return render_template('home.html', error="Name is required")

    if create != False:
        # Tạo mã phòng mới và thêm vào cơ sở dữ liệu
        room_code = generate_room_code(6, list(rooms.keys()))
        new_room = {
            'members': 0,
            'messages': []
        }
        rooms[room_code] = new_room
        try:
            db.execute(text("INSERT INTO rooms (room_code, members, messages) VALUES (:room_code, :members, :messages)"),
                    {"room_code": room_code, "members": 0, "messages": []})
            db.commit()
        except Exception as e:
            return render_template("error.html", message=e)

        session['room'] = room_code
        session['name'] = name
        return redirect(url_for('room'))

    if join:
        # Kiểm tra xem mã phòng có tồn tại trong cơ sở dữ liệu không
        if not code:
            return render_template('home.html', error="Please enter a room code to enter a chat room", name=name)
        if room := db.execute(
            text("SELECT * FROM rooms WHERE room_code LIKE :room_code"),
            {"room_code": code},
        ).fetchone():
            # Lưu thông tin người dùng vào session và chuyển hướng đến route /room
            session['room'] = code
            session['name'] = name
            return redirect(url_for('room'))
        else:
            return render_template('home.html', error="Room code invalid")

    



@app.route('/room')
def room():
    room = session.get('room')
    name = session.get('name')

    if name is None or room is None or room not in rooms:
        return redirect(url_for('home'))

    messages = rooms[room]['messages']
    return render_template('room.html', room=room, user=name, messages=messages)


@socketio.on('connect')
def handle_connect():
    name = session.get('name')
    room = session.get('room')

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
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

        # Xóa phòng ra khỏi cơ sở dữ liệu khi không còn ai trong phòng
        try:
            db.execute(text("DELETE FROM rooms WHERE room_code = :room_code"),
                    {"room_code": room})
            db.commit()
        except Exception as e:
            print("Error deleting room from database:", e)


if __name__ == '__main__':
    socketio.run(app, debug=True)
