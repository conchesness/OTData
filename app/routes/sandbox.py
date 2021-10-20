from app import app
from flask import render_template, redirect, session, flash, url_for
# from app.classes.data import GoogleClassroom, User, Help, Token

@app.route('/sandbox')
def sandbox():
    return render_template('sandbox.html')