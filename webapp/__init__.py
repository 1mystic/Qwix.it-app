from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = '1mystic'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite3'
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024  # 6 MB


db = SQLAlchemy(app)

from .views import *
from .apis import *