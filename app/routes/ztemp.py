from app import app
from flask import render_template, redirect, flash
from app.classes.data import User

@app.route('/fixcsacademy')
def fixcsacademy():
    users = User.objects(cohort = "Oakland Tech - Computer Academy")
    print(len(users))
    for i,user in enumerate(users):
        print(i)
        user.cohort = "Computer Academy"
        user.save()
