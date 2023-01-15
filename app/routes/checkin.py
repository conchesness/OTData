from app import app
from app.routes.sbg import gclass
from .users import credentials_to_dict
from flask import render_template, redirect, session, flash, url_for, request, Markup
from app.classes.data import GEnrollment, User, CheckIn, GoogleClassroom, Help, Token, Settings
from app.classes.forms import BreakForm, CheckInForm, DateForm, StudentWasHereForm, BreakSettingsForm
from .roster import getCourseWork
from datetime import datetime as dt
from datetime import timedelta
from zoneinfo import ZoneInfo
from mongoengine import Q

@app.route("/classdash/<gclassid>", methods=["GET","POST"])
def classdash(gclassid):
    currUser = User.objects.get(pk = session['currUserId'])
    try:
        gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    except Exception as error:
        flash(f"Google Classroom doesn't exist: {error}")
        return redirect(url_for('checkin'))

    # Only get this is the user is a Teacher
    if currUser.role.lower() == "teacher":
        approveHelps = Help.objects(gclass=gClassroom,status="confirmed")
    else:
        approveHelps = None

    query = Q(gclass=gClassroom) & Q(status="asked") & Q(helper__ne = currUser) & Q(requester__ne = currUser)
    helps = Help.objects(query)

    qStatus = ['asked','offered','rejected']
    query = Q(requester=currUser) & Q(gclass=gClassroom) & Q(status__in = qStatus)
    myHelps = Help.objects(query)

    query = Q(helper=currUser) & Q(gclass=gClassroom) & Q(status__in = qStatus)
    myOffers = Help.objects(query)

    query = Q(breakclass=gclassid) & Q(breakstart__exists = True) & Q(breakstart__gt = dt.utcnow() - timedelta(minutes=90))
    try:
        breaks = User.objects(query)
    except:
        breaks = None

    try:
        tokens = Token.objects(owner = currUser).sum('amt')
    except:
        tokens = None

    form = CheckInForm()
    lastCheckIn = CheckIn.objects(student=currUser,gclassid=gclassid).first()

    assigns_choices = []
    numCount = 0
    strCount = 0
    try:
        gClassroom['courseworkdict']['courseWork']
    except:
        result = getCourseWork(gclassid)
        if result == "refresh":
            return redirect(url_for('authorize'))
        elif result == False:
            return redirect(url_for('checkin'))

    if gClassroom['courseworkdict'] and gClassroom['courseworkdict']['courseWork']:
        for ass in gClassroom['courseworkdict']['courseWork']:
            #Check to see if there is a number in the front of the title
            for i,letter in enumerate(ass['title']):
                if letter != ".":
                    try:
                        int(letter)
                    except:
                        break

            if i == 0:
                sortValue = 0
                strCount = strCount + 1
            else:
                sortValue = float(ass['title'][0:i])
                numCount = numCount + 1

            choice = (sortValue,ass['title'])
            assigns_choices.append(choice)
    if strCount > numCount:
        assigns_choices = []
        for ass in gClassroom['courseworkdict']['courseWork']:
            choice = (ass['title'],ass['title'])
            assigns_choices.append(choice)
    else:
        assigns_choices = sorted(assigns_choices, key = lambda i: (i[0]), reverse=True)

    assigns_choices.insert(0, ('other','other'))
    assigns_choices.insert(0, ('','-----'))

    form.assigns.choices = assigns_choices

    if form.validate_on_submit():

        if lastCheckIn and lastCheckIn.gclassid and lastCheckIn.createdate.date() == dt.utcnow().date() and str(lastCheckIn.gclassid) == str(gclassid):
            flash('CHECKIN DID NOT SAVE! It looks like you already checkedin to that class today? If so, please delete one of the checkins.')
            return redirect(url_for('classdash',gclassid=gclassid))
        
        if form.assigns.data == "other" and len(form.other.data) == 0:
            flash("CHECKIN DID NOT SAVE! You chose Other. PLease describe what what you are planning to do!.")
            return redirect(url_for('classdash',gclassid=gclassid))

        googleclass = GoogleClassroom.objects.get(gclassid=gclassid)

        checkin = CheckIn(
            gclassid = gclassid,
            googleclass = googleclass,
            gclassname = googleclass.gclassdict['name'],
            student = currUser,
            desc = form.desc.data,
            status = form.status.data,
            workingon = f"{form.assigns.data} {form.other.data}"
            )
        checkin.save()
        lastCheckIn = checkin

        flash(f"CheckIn for {currUser.fname} {currUser.lname} saved.")

        form.desc.data = None
        form.status.data = None

    breaksettings = Settings.objects().first()

    return render_template('classdash.html',helps=helps, approveHelps=approveHelps, breaks=breaks,tokens=tokens,myHelps=myHelps,myOffers=myOffers, currUser=currUser,gClassroom=gClassroom,lastCheckIn=lastCheckIn,form=form, breaksettings=breaksettings)

@app.route('/breaks/<gclassid>')
def breaks(gclassid):
    query = Q(breakclass=gclassid) & Q(breakstart__exists = True) & Q(breakstart__gt = dt.utcnow() - timedelta(minutes=90))
    try:
        breaks = User.objects(query)
    except:
        breaks = None

    return render_template('breaks.html',classid=gclassid,breaks=breaks)

@app.route("/checkin", methods=['GET', 'POST'])
def checkin():
    currUser = User.objects.get(pk = session['currUserId'])
    enrollments = GEnrollment.objects(owner=currUser)

    return render_template('checkins/checkin.html', enrollments=enrollments, currUser=currUser)

@app.route('/breaksettings/<gClassid>', methods=['GET', 'POST'])
def breaksettings(gClassid):
    form=BreakSettingsForm()
    breakSettings = Settings.objects().first()
    
    # update the settings 
    try:
        breakSettings.update(
            breakCanStart = dt.utcnow().date(),
            currClassEnd = dt.utcnow().date()
        )
    # if there is no settings record, this creates it.
    except:
        Settings(
            breakCanStart = dt.utcnow().date(),
            currClassEnd = dt.utcnow().date()
        ).save()

    if form.validate_on_submit():
        breakStartDT = dt.strptime(f'{form.breakstartdate.data}  {form.breakstarthrs.data}:{form.breakstartmins.data}', '%Y-%m-%d %H:%M')
        breakStartDT = breakStartDT.replace(tzinfo=ZoneInfo('US/Pacific')) 
        classEndDT = dt.strptime(f'{form.classenddate.data}  {form.classendhrs.data}:{form.classendmins.data}', '%Y-%m-%d %H:%M')
        classEndDT = classEndDT.replace(tzinfo=ZoneInfo('US/Pacific'))
        breakSettings.update(
            breakCanStart = breakStartDT,
            currClassEnd = classEndDT
        )
        return redirect(url_for('classdash',gclassid=gClassid))

    return render_template('breaksettings.html',gClassid=gClassid, form=form)
        

@app.route('/breakstart/<gclassid>', methods=['GET', 'POST'])
def breakstart(gclassid):

    currUser = User.objects.get(gid=session['gid'])
    form = BreakForm()

    if currUser.breakstart and dt.now().date() == currUser.breakstart.date() and currUser.breakclass == gclassid:
        flash('You already took a break today.')
        return redirect(url_for('classdash',gclassid=gclassid)) 

    #gEnrollment = GEnrollment.objects.get(gclassroom=gclassid,owner=session['currUserId'])
    #gClass = gEnrollment.gclassroom

    gClass = GoogleClassroom.objects.get(gclassid=gclassid)
    form.gclassid.choices = [(gClass.gclassdict['id'],gClass.gclassdict['name'])]

    try:
        tokencount = Token.objects(owner = currUser).count()
        tokens = Token.objects(owner = currUser)
    except:
        tokencount = 0
        tokens = None

    if form.validate_on_submit():

        if form.duration.data > 10:
            spend = form.duration.data - 10
            if spend > tokencount:
                flash(f"You are trying to spend {spend} tokens but you only have {tokencount}.")
                return redirect(url_for('checkin'))
            for i,token in enumerate(tokens):
                if i+1 <= spend:
                    if token.help:
                        token.help.note = Markup(f"{token.help.note} <br> Token spent on break.")
                    token.delete()

        currUser.update(
            breakstart = dt.now(ZoneInfo('US/Pacific')),
            breakduration = form.duration.data,
            breakclass = form.gclassid.data
        )
        return redirect(url_for('classdash',gclassid=gclassid)) 

    form.duration.data = 10
    return render_template('breakstart.html',tokencount=tokencount, form=form)

# TODO this function should replace checkinstu route and function below
def checkinstus(gclassid,gclassname,student,searchdatetime):
    if session['role'].lower == "student":
        flash("Students can't checkin other studnets.")
        return redirect('index.html')
    currUser = User.objects.get(id=session['currUserId'])

    searchdatetime = searchdatetime.replace(tzinfo=ZoneInfo('UTC')) 

    newCheckIn = CheckIn(
                    gclassname = gclassname,
                    student = student,
                    createdBy = currUser,
                    gclassid = gclassid,
                    desc = f"Check in created by {currUser.fname} {currUser.lname}"
                )
    newCheckIn.save()

    return flash(f" {student.fname} {student.lname} was just checked in by {currUser.fname} {currUser.lname}. ")

@app.route('/deletecheckin/<checkinid>/<returnurl>')
@app.route('/deletecheckin/<checkinid>')
def deletecheckin(checkinid,returnurl='classdash'):
    checkin = CheckIn.objects.get(pk=checkinid)
    gclassid=checkin.googleclass.gclassid

    currUser=User.objects.get(id=session['currUserId'])
    if currUser == checkin.student or currUser.role.lower() == "teacher":
        checkin.delete()
        flash('Checkin deleted')
    else:
        flash("can't delete a checkin you don't own.")

    return redirect(url_for(returnurl, gclassid=gclassid)) 

@app.route('/checkinsfor/<gclassid>', methods=['GET', 'POST'])
def checkinsfor(gclassid,sndrmdr=0):

    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    gclassname = gClassroom.gclassdict['name']

    dateForm = DateForm()
    stuForm = StudentWasHereForm()

    try:
        session['searchdatetime']
    except KeyError:
        searchdate = dt.now(ZoneInfo('US/Pacific')).date()
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
    
    # flask-moment can't recognize timezone and assumes all tz it gets are utc
    # To parse the tz you have to use momentjs which is what I did in the template
    utcsearchdatetime = searchdatetime.astimezone(ZoneInfo("UTC")).date()

    dateForm.querydate.data = searchdatetime.date()

    query = (Q(gclassid = gclassid) & (Q(createdate__gt = utcsearchdatetime) & Q(createdate__lt = utcsearchdatetime + timedelta(days=1))))

    checkins = CheckIn.objects(query)

    enrollments = GEnrollment.objects(gclassroom=gClassroom)

    # This is a list of gids for the students that checked in
    checkingids = [checkin.student.gid for checkin in checkins]

    # This is a list of gids for the students in the Google Classroom
    rostergids = [enrollment.owner.id for enrollment in enrollments]

    # This is a list of gids for of students on the google roster but not in the checked in
    notcheckedingids = [rostergid for rostergid in rostergids if rostergid not in checkingids]

    notcheckedstus = []
    notcheckedstuschoices = []

    for enrollment in enrollments:
        if enrollment.owner.id in notcheckedingids:
            try:
                notcheckedstus.append(enrollment.owner)
            except:
                flash(f"{enrollment} may not have an account in OTData or you may need to update the roster for this class.")
            else:
                if enrollment.sortCohort == "~":
                    sortCohort = ""
                else:
                    sortCohort = enrollment.sortCohort + ':'
                notcheckedstuschoices.append((enrollment.owner.aeriesid,Markup(f"{sortCohort} {enrollment.owner.lname}, {enrollment.owner.fname} <a href='/profile/{enrollment.owner.aeriesid}'>&#128279;</a>")))

    # If there are students who did not checkin get a list of all their user objects

    # sort the list of tuples by its second item which is student's name
    notcheckedstuschoices = sorted(notcheckedstuschoices, key = lambda i: (i[1]))

    stuForm.student.choices = notcheckedstuschoices

    if request.form and 'submitStuForm' in request.form and len(stuForm.student.data)>0:
        for stu in stuForm.student.data:
            student = User.objects.get(aeriesid=stu)
            checkinstus(gclassid,gclassname,student,searchdatetime)
        request.form = None
        return redirect(url_for('checkinsfor', gclassid=gclassid)) 
    
    return render_template('checkins/checkinsfor.html', querydate= dateForm.querydate.data, checkins=checkins, stuForm=stuForm, dateForm=dateForm, gclassid=gclassid, gclassname=gclassname, notcheckedstus=notcheckedstus, searchdatetime=searchdatetime)


@app.route('/checkinssince/<gclassid>', methods=['GET', 'POST'])
def checkinssince(gclassid):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    gclassname = gClassroom.gclassdict['name']
    dateForm = DateForm()
    searchdate = dt.now(ZoneInfo('US/Pacific')).date()

    try:
        searchdatetime = session['searchdatetime']
    except KeyError:
        searchdate = dt.now(ZoneInfo('US/Pacific')).date()

    #dateForm.querydate.data = searchdatetime.date()

    if dateForm.validate_on_submit():
        # get the date from the form
        searchdate = dateForm.querydate.data
        # turn the date in to a datetime 
        searchdatetime = dt(searchdate.year, searchdate.month, searchdate.day)
        session['searchdatetime'] = searchdatetime
    
    utcsearchdatetime = searchdatetime.astimezone(ZoneInfo("UTC")).date()

    query = (Q(gclassid = gclassid) & (Q(createdate__gt = utcsearchdatetime)))

    checkins = CheckIn.objects(query)

    users = []
    for checkin in checkins:
        users.append(checkin.student)
    users = list(set(users))
    usersdict = {}
    for user in users:
        usersdict[user] = "X"
    for checkin in checkins:
        if usersdict[checkin.student] == "X":
            usersdict[checkin.student] = [checkin]
        else:
            usersdict[checkin.student].append(checkin)
    
    newdict = {}
    for user in usersdict:
        total = 0
        length = len(usersdict[user])
        for checkin in usersdict[user]:
            total = total + int(checkin.status)
        newdict[user] = [length,round(total/length,2)]
    usersdict = newdict

    usersdict = sorted(usersdict.items(), key=lambda e: e[1][1])



    return render_template('checkins/checkinsforsince.html', querydate= dateForm.querydate.data, checkins=checkins, dateForm=dateForm, gclassid=gclassid, searchdatetime=searchdatetime, usersdict=usersdict, gclassname=gclassname)
