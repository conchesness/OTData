# Every level/folder of a Python application has an __init__.py file. The purpose of this file is to connect the levels
# of the app to each other. 

from mongoengine import *
from flask import Flask
import os
from flask_moment import Moment
import base64

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") # or os.urandom(20)
# you must change the next line to be link to your database at mlab
connect("otdata", host='mongodb+srv://admin:bulldogz@cluster0-8m0v1.gcp.mongodb.net/otdata?retryWrites=true&w=majority')

moment = Moment(app)

def base64encode(img):
    image = base64.b64encode(img)
    image = image.decode('utf-8')
    return image

app.jinja_env.globals.update(base64encode=base64encode)

from .routes import *
