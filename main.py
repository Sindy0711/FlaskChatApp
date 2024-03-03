import os
from flask import Flask  
from flask_session import Session
from flask_socketio import SocketIO
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session,sessionmaker
from models import db 

from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = 'SDKFJSDFOWEIOF'
socketio = SocketIO(app)   

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))
app.config['SESSION_PERMANENT'] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


def cleanup_session(exception=None):
    db.remove()

from routes import *

if __name__ == '__main__':
    
    socketio.run(app, debug=True)
