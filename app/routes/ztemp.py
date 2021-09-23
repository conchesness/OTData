# from app import app
# from flask import render_template, redirect, flash
# from app.classes.data import User
# import pandas as pd

# @app.route('/alumni')
# def alumni():
#     alumni = User.objects(grade__gt = 11, personalemail__exists = True)

#     return render_template('logins.html',logins=alumni)