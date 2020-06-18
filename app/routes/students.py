from app import app
from .scopes import *

from flask import render_template, redirect, url_for, request, session, flash, Markup
from app.classes.data import User, Config
from app.classes.forms import UserForm, AdultForm
from .credentials import GOOGLE_CLIENT_CONFIG
from requests_oauth2.services import GoogleClient
from requests_oauth2 import OAuth2BearerToken
from mongoengine import Q
from bson.objectid import ObjectId
import requests
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import os

@app.route('/students/<lname>/<fname>')
@app.route('/students/<lname>')
def students(fname=None,lname=None):

    if fname:
        query = Q(afname__contains=fname) and Q(alname__contains=lname)
    else:
        query = Q(alname__contains=lname)

    students = User.objects(query)

    return render_template('students.html',students=students)
