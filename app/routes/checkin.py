from app import app
from .users import credentials_to_dict
from flask import render_template, redirect, session, flash, url_for, request, Markup
from app.classes.data import User, CheckIn, GoogleClassroom, Help, Token
from app.classes.forms import CheckInForm, DateForm, StudentWasHereForm
from datetime import datetime as dt
from datetime import timedelta
from mongoengine import Q
import pytz as pytz
import google.oauth2.credentials
import googleapiclient.discovery
from google.auth.exceptions import RefreshError
from twilio.rest import Client
from .credentials import twilio_account_sid, twilio_auth_token


@app.route("/checkin", methods=['GET', 'POST'])
def checkin():

    form = CheckInForm()
    
    currUser = User.objects.get(pk = session['currUserId'])

    gCourses = currUser.gclasses
    
    gclasses = []
    for gCourse in gCourses:
        if gCourse.gclassroom:
            tempname = gCourse.gclassroom.gclassdict['name']
            if not gCourse.status:

                gCourse.status = ""

            # a list of tuples for the form
            if gCourse.status == "Active":
                gclasses.append((gCourse.gclassroom.gclassid, tempname))

    form.gclassid.choices = gclasses
    
    if form.validate_on_submit() and currUser.role.lower() == 'student':

        lastCheckIn = CheckIn.objects(student=currUser,gclassid=form.gclassid.data).first()

        # nowPacific = nowUTC.astimezone(timezone('US/Pacific'))
        # All dates retrieved from the DB are in UTC
        if lastCheckIn and lastCheckIn.createdate.date() == dt.now(pytz.utc).date() and lastCheckIn.gclassid == int(form.gclassid.data):
            flash('It looks like you already checkedin to that class today? If so, please delete one of the checkins.')
            return redirect(url_for('checkin'))

        if len(form.status.data) == 0:
            flash('"How are you" is a required field')
            return redirect(url_for('checkin'))

        googleclass = GoogleClassroom.objects.get(gclassid=form.gclassid.data)

        checkin = CheckIn(
            gclassid = form.gclassid.data,
            googleclass = googleclass,
            gclassname = googleclass.gclassdict['name'],
            student = currUser,
            desc = form.desc.data,
            status = form.status.data         
            )
        
        checkin.save()
        flash(f"CheckIn for {currUser.fname} {currUser.lname} saved.")

        form.gclassid.data = None
        form.desc.data = None
        form.status.data = None

    if currUser.role.lower() == 'student':
        checkins = CheckIn.objects(student=currUser).order_by('-createdate').limit(10)
    else:
        checkins = None
        form = None

    query = Q(breakstart__exists = True) & Q(breakstart__gt = dt.utcnow() - timedelta(minutes=90))
    try:
        breaks = User.objects(query)
    except:
        breaks = None

    query = Q(requester=currUser) & Q(status__ne = "confirmed")
    try:
        myHelps = Help.objects(query)
    except:
        myHelps = None

    query = Q(helper=currUser) & Q(status__ne = "confirmed")
    try:
        myOffers = Help.objects(query)
    except:
        myOffers = None

    query = Q(requester__ne = currUser) & Q(helper__ne = currUser) & (Q(status="asked") | Q(status="offered"))
    helps = Help.objects(query)
    try:
        helps = Help.objects(query)
    except:
        helps=None
    try:
        tokens = Token.objects(owner = currUser).count()
    except:
        tokens = None

    print(tokens)

    return render_template('checkin.html', breaks=breaks, myHelps=myHelps, myOffers=myOffers, helps=helps, gCourses=gCourses, form=form, checkins=checkins, currUser=currUser, tokens=tokens)

@app.route('/breakstart')
def breakstart():
    currUser = User.objects.get(gid=session['gid'])
    currUser.update(
        breakstart = dt.now(pytz.timezone('US/Pacific'))
    )
    return redirect(url_for('checkin')) 

# TODO this function should replace checkinstu route and function below
def checkinstus(gclassid,gclassname,student,searchdatetime):
    if session['role'].lower == "student":
        flash("Students can't checkin other studnets.")
        return redirect('index.html')
    currUser = User.objects.get(id=session['currUserId'])

    searchdatetime = searchdatetime.astimezone(pytz.utc)
    #searchdatetime = searchdatetime - timedelta(hours = searchdatetime.hour)
    #Since 4pm is the latest checkin time I set the time after that for manual checkin
    searchdatetime = searchdatetime + timedelta(hours = 20, minutes = 1)

    newCheckIn = CheckIn(
                    createdate = searchdatetime,
                    gclassname = gclassname,
                    student = student,
                    createdBy = currUser,
                    gclassid = gclassid,
                    desc = f"Check in created by {currUser.fname} {currUser.lname}"
                )
    newCheckIn.save()
    return flash(f" {student.fname} {student.lname} was just checked in by {currUser.fname} {currUser.lname}. ")

@app.route('/deletecheckin/<checkinid>/<gclassid>/<gclassname>')
@app.route('/deletecheckin/<checkinid>')
def deletecheckin(checkinid,gclassid=None,gclassname=None):
    checkin = CheckIn.objects.get(pk=checkinid)
    checkin.delete()
    if gclassid and gclassname:
        return redirect(url_for('checkinsfor', gclassid=gclassid,gclassname=gclassname)) 

    return redirect(url_for('checkin'))

@app.route('/checkinsfor/<gclassid>/<sndrmdr>', methods=['GET', 'POST'])
@app.route('/checkinsfor/<gclassid>', methods=['GET', 'POST'])
def checkinsfor(gclassid,sndrmdr=0):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    gclassname = gClassroom.gclassdict['name']

    sndrmdr = int(sndrmdr)
    dateForm = DateForm()
    stuForm = StudentWasHereForm()

    try:
        session['searchdatetime']
    except KeyError:
        searchdate = dt.now(pytz.timezone('US/Pacific')).date()
        searchdatetime = dt(searchdate.year, searchdate.month, searchdate.day)
        session['searchdatetime'] = searchdatetime
    
    if dateForm.submitDateForm.data and dateForm.validate_on_submit():
        # get the date from the form
        searchdate = dateForm.querydate.data
        # turn the date in to a datetime 
        searchdatetime = dt(searchdate.year, searchdate.month, searchdate.day)
        session['searchdatetime'] = searchdatetime
    else:
        searchdatetime = session['searchdatetime']

    tz = pytz.timezone('US/Pacific')
    searchdatetime = tz.localize(searchdatetime)

    dateForm.querydate.data = searchdatetime.date()

    query = (Q(gclassid = gclassid) & (Q(createdate__gt = searchdatetime) & Q(createdate__lt = searchdatetime + timedelta(days=1))) )
    checkins = CheckIn.objects(query)
    print(len(f"checkins"))

    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')
    session['credentials'] = credentials_to_dict(credentials)
    classroom_service = googleapiclient.discovery.build('classroom', 'v1', credentials=credentials)
    students = []
    pageToken = None
    try:
        students_results = classroom_service.courses().students().list(courseId = gclassid,pageToken=pageToken).execute()
    except RefreshError:
        flash("When I asked for the courses from Google Classroom I found that your credentials needed to be refreshed.")
        return redirect('/authorize')

    while True:
        pageToken = students_results.get('nextPageToken')
        students.extend(students_results['students'])
        if not pageToken:
            break
        students_results = classroom_service.courses().students().list(courseId = gclassid,pageToken=pageToken).execute()


    # This is a list of gids for the students that checked in
    checkingids = [checkin.student.gid for checkin in checkins]

    # This is a list of gids for teh students in the Google Classroom
    rostergids = [student['userId'] for student in students]

    # This is a list of gids for of students on the google roster but not in the checked in
    notcheckedingids = [rostergid for rostergid in rostergids if rostergid not in checkingids]
    
    # If there are students who did not checkin get a list of all their user objects
    notcheckedstus = []
    notcheckedstuschoices = []
    if notcheckedingids:
        for notcheckedingid in notcheckedingids:
            try:
                aStu = User.objects.get(gid = notcheckedingid)
            except:
                # Check for students that have never logged in to OTData so they don't have a gid
                # TODO check these id's back against the students 
                for stu in students:
                    if stu['userId'] == notcheckedingid and stu['profile']['emailAddress'][:2]=='s_':
                        try:
                            temp = User.objects.get(otemail = stu['profile']['emailAddress'])
                        except Exception as error:
                            flash(f"Unknown error for {stu['profile']['emailAddress']}: {error}")
                            break
                        notcheckedstus.append(temp)
                        notcheckedstuschoices.append((temp.aeriesid,Markup(f'{temp.lname}, {temp.fname}<a href="/profile/{temp.aeriesid}">&#128279;</a>')))
                        break
            else:
                if aStu.role.lower() == "student":
                    try:
                        stuGClass = aStu.gclasses.get(gclassid=gclassid)
                    except:
                        notcheckedstuschoices.append((aStu.aeriesid,Markup(f'{aStu.lname}, {aStu.fname} <a href="/profile/{aStu.aeriesid}">&#128279;</a>')))
                    else:
                        if stuGClass.sortcohort:
                            sortCohort = stuGClass.sortcohort
                            setattr(aStu, 'sortCohort', sortCohort)
                        else:
                            sortCohort = ""
                        notcheckedstuschoices.append((aStu.aeriesid,Markup(f'{sortCohort} {aStu.lname}, {aStu.fname} <a href="/profile/{aStu.aeriesid}">&#128279;</a>')))
                    notcheckedstus.append(aStu)

    # sort the list of tuples by its second item which is student's name
    lst = len(notcheckedstuschoices)  
    for i in range(0, lst):  
        for j in range(0, lst-i-1):  
            if (notcheckedstuschoices[j][1] > notcheckedstuschoices[j + 1][1]):  
                temp = notcheckedstuschoices[j]  
                notcheckedstuschoices[j]= notcheckedstuschoices[j + 1]  
                notcheckedstuschoices[j + 1]= temp  

    stuForm.student.choices = notcheckedstuschoices

    if request.form and 'submitStuForm' in request.form and len(stuForm.student.data)>0:
        for stu in stuForm.student.data:
            student = User.objects.get(aeriesid=stu)
            checkinstus(gclassid,gclassname,student,searchdatetime)
        request.form = None
        return redirect(url_for('checkinsfor', gclassid=gclassid,gclassname=gclassname)) 

    if len(notcheckedstus) > 0 and sndrmdr == 1:
        client = Client(twilio_account_sid, twilio_auth_token)
        # TODO should probably make sure these are the same timezone
        if searchdatetime.date() == dt.now(pytz.timezone('US/Pacific')).date():
            for stu in notcheckedstus:
                if stu.mobile:
                    client.messages.create(
                            body=f"Please Check in for {gclassname}.",
                            from_='+15108043552',
                            to=stu.mobile
                        )
                    flash(f'txt sent to {stu.fname} {stu.lname}.')
        else:
            flash('You can only send checkin reminders for the current day.')

    return render_template('checkinsfor.html', querydate= dateForm.querydate.data, checkins=checkins, stuForm=stuForm, dateForm=dateForm, gclassid=gclassid, gclassname=gclassname, notcheckedstus=notcheckedstus, searchdatetime=searchdatetime)
