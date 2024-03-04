
from werkzeug.security import generate_password_hash, check_password_hash
from main import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False)
    members = db.Column(db.Integer, default=0)
    messages = db.relationship('Message', backref='room', lazy=True)
    

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200))
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    
class Join(db.Model):
    __tablename__ = 'joins'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)

    # Định nghĩa quan hệ với bảng Users và Rooms
    user = db.relationship("User", backref=db.backref("joins", cascade="all, delete-orphan"))
    room = db.relationship("Room", backref=db.backref("joins", cascade="all, delete-orphan"))

def __repr__(self):
    return f"<Join user_id={self.user_id} room_id={self.room_id}>"