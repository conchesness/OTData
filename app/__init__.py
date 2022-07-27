# Every level/folder of a Python application has an __init__.py file. The purpose of this file is to connect the levels
# of the app to each other. 

from mongoengine import connect
from flask import Flask
import os
from flask_moment import Moment
import base64
import re

app = Flask(__name__)
#app.jinja_options['extensions'].append('jinja2.ext.do')
app.jinja_env.add_extension('jinja2.ext.do')
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") # or os.urandom(20)
# you must change the next line to be link to your database at mongodb.com
# connect("otdata", host=f"{os.environ.get('mongodb_host')}/otdata?retryWrites=true&w=majority")
# Sandbox DB
connect("otdatasb", host=f"{os.environ.get('mongodb_host')}/otdatasb?retryWrites=true&w=majority")

moment = Moment(app)

def base64encode(img):

    image = base64.b64encode(img)
    image = image.decode('utf-8')
    return image

# Function to format phone numbers for UI
def formatphone(phnum):
    phnum = str(phnum)
    phnum = f"({phnum[0:3]}) {phnum[3:6]}-{phnum[6:]}"
    return phnum

# Function to format phone numbers to ints
def formatphonenums(phstr):
    phstr = re.sub("[^0-9]", "", phstr)

    return (phstr)

app.jinja_env.globals.update(base64encode=base64encode, formatphone=formatphone, formatphonenums=formatphonenums)

from .routes import *
