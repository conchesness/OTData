from app import app
from .scopes import *

from flask import render_template, redirect, url_for, request, session, flash, Markup
from app.classes.data import User
from app.classes.forms import StudentForm, SendemailForm
from mongoengine import Q
import requests
from googleapiclient.discovery import build
import google.oauth2.credentials
import google_auth_oauthlib.flow
# import googleapiclient.discovery
from requests_oauth2.services import GoogleClient
from requests_oauth2 import OAuth2BearerToken
import os.path
import base64
from email.mime.text import MIMEText
from urllib.error import HTTPError

@app.route('/findstudent', methods=['GET', 'POST'])
def findstudent():

    students = None

    form = StudentForm()
    if form.validate_on_submit():
        query3 = Q(role__icontains = 'Student')

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

    if fname:
        query = Q(afname__contains=fname) and Q(alname__contains=lname)
    else:
        query = Q(alname__contains=lname)

    students = User.objects(query)

    return render_template('students.html',students=students)

@app.route('/sendstudentemail/<aeriesid>', methods=['GET','POST'])
def sendstudentemail(aeriesid):

    try:
        student = User.objects.get(aeriesid = aeriesid)
    except:
        # This would only happen if they typed the aeries id in to the url themselves and got it wrong.
        flash('The student you are trying to find does not exist.')
        return redirect('/')
    
    emailList = []
    # add the student
    emailList.append((student.otemail,student.otemail))

    # add adults
    if student.aadultemail:
        emailList.append((student.aadultemail,student.aadultemail))
    if student.adults:
        for adult in student.adults:
            if adult.email and adult.altemail:
                emailList.append((adult.email,adult.email))
                emailList.append((adult.altemail,adult.altemail))
            elif adult.email:
                emailList.append((adult.email,adult.email))
            elif adult.altemail:
                emailList.append((adult.altemail,adult.altemail))

    # add the teachers
    if student.sections:
        for section in student.sections:
            emailList.append((section.teacher.otemail,section.teacher.otemail))

    form = SendemailForm()
    form.to.choices = emailList
    form.cc.choices = emailList

    if form.validate_on_submit():
        if google.oauth2.credentials.Credentials(**session['credentials']).valid:
            credentials = google.oauth2.credentials.Credentials(**session['credentials'])
        else:
            return redirect('authorize')
        service = build('gmail', 'v1', credentials=credentials)

        emailToString = ""
        for email in form.to.data:
            emailToString = emailToString + email + ", "

        emailCCString = ""
        for email in form.cc.data:
            emailCCString = emailCCString + email + ", "


        # Call the Gmail API
        message = MIMEText(form.body.data)
        message['to'] = emailToString
        message['cc'] = emailCCString
        message['from'] = session['email']
        message['subject'] = form.subject.data
        b64_bytes = base64.urlsafe_b64encode(message.as_bytes())
        b64_string = b64_bytes.decode()
        message = {'raw' : b64_string}

        try:
            message = (service.users().messages().send(userId='me', body=message)
                    .execute())
            msgSent = True
        except:
            flash('Something went wrong')

        if msgSent:
            currUser = User.objects.get(id=session['currUserId'])
            student.communications.create(
                type_ = "email",
                to = emailToString + emailCCString,
                fromadd = session['email'],
                fromwho = currUser,
                subject = form.subject.data,
                body = form.body.data
            )
            student.save()
        return redirect(url_for('profile',aeriesid=aeriesid))

    return render_template('sendstudentemail.html', form=form, emailList=emailList, student=student)
