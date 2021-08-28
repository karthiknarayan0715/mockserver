from flask import Flask
from flaskext.mysql import MySQL
import os

app = Flask(__name__)
mysql = MySQL(app)

app.config['SECRET_KEY'] = 'key'
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'Pass@1234'
app.config['MYSQL_DATABASE_DB'] = 'hackathondb'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

from files import routes