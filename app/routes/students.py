from app import app
from .users import credentials_to_dict
from flask import render_template, redirect, url_for, session, flash, Markup
from app.classes.data import User
from app.classes.forms import StudentForm, SendemailForm, StudentNoteForm
from mongoengine import Q
from googleapiclient.discovery import build
import google.oauth2.credentials
from google.auth.exceptions import RefreshError
import base64
from email.mime.text import MIMEText
from bson.objectid import ObjectId


@app.route('/findstudent', methods=['GET', 'POST'])
def findstudent():

    students = None

    form = StudentForm()
    if form.validate_on_submit():
        query3 = Q(role__icontains = 'Student')

        if form.aeriesid.data:
            query =  Q(aeriesid = form.aeriesid.data)
        elif len(form.fname.data)>0 and len(form.lname.data)>0:
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
            flash("You didn't enter any names.")
            return render_template('findstudent.html', form=form)

        students = User.objects(query)
        if form.aeriesid.data and len(students) == 0:
            flash(Markup(f"That ID is not in this database. <a target='_blank' href='https://aeries.ousd.org/Helpers/SetStudentAndRedirect.aspx?ID={form.aeriesid.data}&DU=StudentProfile.aspx'>Check Aeries</a><br> If you get a response that says 'If you are reading this, a redirect did not happen correctly.' it is probably because it is not in Aeries either."))
            return render_template('findstudent.html', form=form)
        elif len(students) == 0:
            flash("Your search did not find any students.")
            return render_template('findstudent.html', form=form)

        return render_template('findstudent.html', form=form, students=students)

    return render_template('findstudent.html', form=form)

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
    emailList.append((student.otemail,Markup(f"<b>Student:</b> {student.otemail}")))

    if student.personalemail:
        emailList.append((student.personalemail,Markup(f"<b>Student Personal Email:</b> {student.personalemail}")))
        
    # add adults
    if student.aadultemail:
        emailList.append((student.aadultemail,Markup(f"<b>Aeries Parent:</b> {student.aadults}<br>({student.aadultemail})")))
    if student.adults:
        for adult in student.adults:
            if adult.email and adult.altemail:
                emailList.append((adult.email,Markup(f"<b>{adult.relation}:</b> {adult.fname} {adult.lname}<br>({adult.email})")))
                emailList.append((adult.altemail,Markup(f"<b>{adult.relation}</b> (Alt Email): {adult.fname} {adult.lname}<br>({adult.altemail})")))
            elif adult.email:
                emailList.append((adult.email,Markup(f"<b>{adult.relation}:</b> {adult.fname} {adult.lname}<br>({adult.email})")))
            elif adult.altemail:
                emailList.append((adult.altemail,Markup(f"<b>{adult.relation}</b> (Alt Email): {adult.fname} {adult.lname}<br>({adult.altemail})")))

    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')

    session['credentials'] = credentials_to_dict(credentials)

    # add teachers from the gclasses embedded doc
    emailList2=[]
    if student.gclasses:
        for gclass in student.gclasses:
            if gclass.gclassroom:
                try:
                    teacheremail = gclass.gclassroom.gteacherdict['emailAddress']
                except:
                    teacheremail = None
                if not gclass.status:
                    gclass.tempstatus = ""
                else:
                    gclass.tempstatus = f"({gclass.status}) "
                if gclass.status =="Active":
                    if teacheremail:
                        emailList.append((teacheremail,Markup(f"<b>{gclass.tempstatus}{gclass.gclassroom.gclassdict['name']}:</b> {gclass.gclassroom.gteacherdict['name']['givenName']} {gclass.gclassroom.gteacherdict['name']['familyName']}")))
                elif teacheremail and not gclass.status == "Ignore":
                        emailList2.append((teacheremail,Markup(f"<b>{gclass.tempstatus}{gclass.gclassroom.gclassdict['name']}:</b> {gclass.gclassroom.gteacherdict['name']['givenName']} {gclass.gclassroom.gteacherdict['name']['familyName']}")))
        if len(emailList2) > 0:
            emailList = emailList + emailList2

    form = SendemailForm()
    form.to.choices = emailList
    form.cc.choices = emailList

    if form.validate_on_submit():
        if google.oauth2.credentials.Credentials(**session['credentials']).valid:
            credentials = google.oauth2.credentials.Credentials(**session['credentials'])
        else:
            return redirect('/authorize')

        session['credentials'] = credentials_to_dict(credentials)
        service = build('gmail', 'v1', credentials=credentials)

        emailToString = ""
        if form.to.data:
            for email in form.to.data:
                emailToString = emailToString + email + ", "

        if form.otherto.data:
            emailToString = emailToString + form.otherto.data

        emailCCString = ""
        if form.cc.data:
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
            message = (service.users().messages().send(userId='me', body=message).execute())
            flash("Email was sent. You can see the email in your GMail outbox and also below on this page in the 'Activities' secion.")
        except RefreshError:
            flash('Something went wrong. The problem is likely that you need to tell Google that this app is autorized to send emails. Hopefully that is fixed now')
            return redirect('/authorize')
            # return render_template('sendstudentemail.html', form=form, emailList=emailList, student=student)

        currUser = User.objects.get(id=session['currUserId'])
        # If the student was included in the email or the student sent the email it should not be tagged confidential
        if student.otemail in form.to.data or student.otemail == session['email']:
            confidential = False
        else:
            confidential = True

        student.communications.create(
            oid = ObjectId(),
            type_ = "email",
            to = emailToString + emailCCString,
            fromadd = session['email'],
            fromwho = currUser,
            subject = form.subject.data,
            body = form.body.data,
            confidential = confidential
        )
        student.save()
        return redirect(url_for('profile',aeriesid=aeriesid))

    return render_template('sendstudentemail.html', form=form, emailList=emailList, student=student)

@app.route('/deletecommunication/<aeriesid>/<commid>')
def deletecomm(aeriesid,commid):
    editUser = User.objects.get(aeriesid=aeriesid)
    delComm = editUser.communications.get(oid=commid)
    editUser.communications.filter(oid=commid).delete()
    editUser.communications.filter(oid=commid).save()
    flash(f"Communication record {delComm.oid} was deleted")
    
    return redirect(url_for('profile', aeriesid=aeriesid))

@app.route('/studentnote/<aeriesid>', methods=['GET','POST'])
def studentnote(aeriesid):
    student = User.objects.get(aeriesid = aeriesid)
    currUser = User.objects.get(id = session['currUserId'])
    form = StudentNoteForm()

    if form.validate_on_submit():
        student.notes.create(
            oid = ObjectId(),
            content = form.content.data,
            author = currUser,
            type_ = form.type_.data,
            date = form.date.data
        )
        student.save()
        return redirect(url_for('profile',aeriesid=aeriesid))

    return render_template("studentnoteform.html", form=form, student=student,currUser=currUser)

@app.route('/deletenote/<aeriesid>/<noteoid>')
def deletenote(aeriesid,noteoid):
    editUser = User.objects.get(aeriesid=aeriesid)
    delNote = editUser.notes.get(oid=noteoid)
    editUser.notes.filter(oid=noteoid).delete()
    editUser.notes.filter(oid=noteoid).save()
    flash(f"Communication record {delNote.oid} was deleted")
    
    return redirect(url_for('profile', aeriesid=aeriesid))

@app.route('/compscisrs')
def compscisrs():
    srs=User.objects(cohort__icontains = "computer", grade = 12)
    return render_template('compscisrs.html',srs=srs)