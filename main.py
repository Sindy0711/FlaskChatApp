import os
from flask import Flask  
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session



from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SDKFJSDFOWEIOF')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SESSION_PERMANENT'] = False
app.config["SESSION_TYPE"] = "filesystem"


db = SQLAlchemy(app)
socketio = SocketIO(app)   
Session(app)




from routes import *

if __name__ == '__main__':
    socketio.run(app, debug=True)
