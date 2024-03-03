from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random
from string import ascii_letters
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True)
    members = db.Column(db.Integer, default=0)
    messages = db.relationship('Message', backref='room', lazy=True)
    
    @staticmethod
    def generate_room_code(length: int, existing_codes: list[str]) -> str:
        while True:
            code_chars = [random.choice(ascii_letters) for _ in range(length)]
            code = ''.join(code_chars)

            if code not in existing_codes:
                return code

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200))
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)