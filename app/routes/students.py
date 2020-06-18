from app import app
from .scopes import *

from flask import render_template, redirect, url_for, request, session, flash, Markup
from app.classes.data import User
from app.classes.forms import StudentForm
from mongoengine import Q
import requests

@app.route('/findstudent', methods=['GET', 'POST'])
def findstudent():
    if session['role'].lower() == "student":
        return redirect(url_for('profile'))

    students = None

    form = StudentForm()
    if form.validate_on_submit():
        query3 = Q(role='Student')

        if len(form.fname.data)>0 and len(form.lname.data)>0:
            query1 = Q(afname__icontains = form.fname.data) | Q(ufname__icontains = form.fname.data)
            query2 = Q(alname__icontains = form.lname.data) | Q(ulname__icontains = form.lname.data)
            query = query1 & query2 & query3
        elif len(form.fname.data)>0 and len(form.lname.data)==0:
            query1 = Q(afname__icontains = form.fname.data) | Q(ufname__icontains = form.fname.data)
            query = query1 & query3
        elif len(form.fname.data)==0 and len(form.lname.data)>0:
            query2 = Q(alname__icontains = form.lname.data) | Q(ulname__icontains = form.lname.data)
            query = query2 & query3
        else:
            flash(f"You didn't enter any names.")
            return render_template('findstudent.html', form=form)

        students = User.objects(query)

        return render_template('findstudent.html', form=form, students=students)

    return render_template('findstudent.html', form=form)

@app.route('/students/<lname>/<fname>')
@app.route('/students/<lname>')
def students(fname=None,lname=None):
    if session['role'].lower() == "student":
        return redirect(url_for('profile'))
        
    if fname:
        query = Q(afname__contains=fname) and Q(alname__contains=lname)
    else:
        query = Q(alname__contains=lname)

    students = User.objects(query)

    return render_template('students.html',students=students)

