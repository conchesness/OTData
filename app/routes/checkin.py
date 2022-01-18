from app import app
from .users import credentials_to_dict
from flask import render_template, redirect, session, flash, url_for, request, Markup
from app.classes.data import User, CheckIn, GoogleClassroom, Help, Token
from app.classes.forms import BreakForm, CheckInForm, DateForm, StudentWasHereForm
from .roster import getCourseWork
from datetime import datetime as dt
from datetime import timedelta
from mongoengine import Q
import pytz as pytz

@app.route("/classdash/<gclassid>", methods=["GET","POST"])
def classdash(gclassid):
    currUser = User.objects.get(pk = session['currUserId'])
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)

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
        getCourseWork(gclassid)

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
        flash("Assignments are sorted numerically.")
        assigns_choices = sorted(assigns_choices, key = lambda i: (i[0]), reverse=True)

    assigns_choices.insert(0, ('other','other'))
    assigns_choices.insert(0, ('','-----'))

    form.assigns.choices = assigns_choices

    #if form.validate_on_submit() and currUser.role.lower() == 'student':
    if form.validate_on_submit():

        # nowPacific = nowUTC.astimezone(timezone('US/Pacific'))
        # All dates retrieved from the DB are in UTC

        if lastCheckIn and lastCheckIn.gclassid and lastCheckIn.createdate.date() == dt.now(pytz.utc).date() and str(lastCheckIn.gclassid) == str(gclassid):
            flash('It looks like you already checkedin to that class today? If so, please delete one of the checkins.')
            return redirect(url_for('classdash',gclassid=gclassid))

        if len(form.status.data) == 0:
            flash('"How are you" is a required field')
            return redirect(url_for('classdash',gclassid=gclassid))
        
        if form.assigns.data == "other" and len(form.desc.data) == 0:
            flash("If you choose Other please describe what you are doing.")
            return redirect(url_for('classdash',gclassid=gclassid))

        googleclass = GoogleClassroom.objects.get(gclassid=gclassid)

        checkin = CheckIn(
            gclassid = gclassid,
            googleclass = googleclass,
            gclassname = googleclass.gclassdict['name'],
            student = currUser,
            desc = f"{form.assigns.data} {form.desc.data}",
            status = form.status.data         
            )
        
        checkin.save()
        lastCheckIn = checkin
        flash(f"CheckIn for {currUser.fname} {currUser.lname} saved.")

        form.desc.data = None
        form.status.data = None

    return render_template('classdash.html',helps=helps, approveHelps=approveHelps, breaks=breaks,tokens=tokens,myHelps=myHelps,myOffers=myOffers, currUser=currUser,gClassroom=gClassroom,lastCheckIn=lastCheckIn,form=form)

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
    gCourses = currUser.gclasses

    return render_template('checkin.html', gCourses=gCourses, currUser=currUser)

@app.route('/breakstart/<gclassid>', methods=['GET', 'POST'])
def breakstart(gclassid):

    currUser = User.objects.get(gid=session['gid'])
    form = BreakForm()

    if currUser.breakstart and dt.now().date() == currUser.breakstart.date() and currUser.breakclass == gclassid:
        flash('You already took a break today.')
        return redirect(url_for('classdash',gclassid=gclassid)) 

    gClass = currUser.gclasses.filter(gclassid=gclassid)
    gClass = gClass[0]

    form.gclassid.choices = [(gClass.gclassid,gClass.classname)]

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
                    token.delete()

        currUser.update(
            breakstart = dt.now(pytz.timezone('US/Pacific')),
            breakduration = form.duration.data,
            breakclass = form.gclassid.data
        )
        #return redirect(url_for('checkin')) 
        return redirect(url_for('classdash',gclassid=gclassid)) 

    form.duration.data = 10
    return render_template('breakstart.html',tokencount=tokencount, form=form)

# TODO this function should replace checkinstu route and function below
def checkinstus(gclassid,gclassname,student,searchdatetime):
    if session['role'].lower == "student":
        flash("Students can't checkin other studnets.")
        return redirect('index.html')
    currUser = User.objects.get(id=session['currUserId'])

    searchdatetime = searchdatetime.astimezone(pytz.utc)
    #searchdatetime = searchdatetime - timedelta(hours = searchdatetime.hour)
    #Since 4pm is the latest checkin time I set the time after that for manual checkin
    #searchdatetime = searchdatetime + timedelta(hours = 20, minutes = 1)

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
    currUser=User.objects.get(id=session['currUserId'])
    if currUser == checkin.student or currUser.role.lower() == "teacher":
        checkin.delete()
        flash('Checkin deleted')
    else:
        flash("can't delete a checkin you don't own.")
    if gclassid and gclassname:
        return redirect(url_for('checkinsfor', gclassid=gclassid,gclassname=gclassname)) 

    return redirect(url_for('classdash',gclassid=checkin.googleclass.gclassid))

@app.route('/checkinsfor/<gclassid>', methods=['GET', 'POST'])
def checkinsfor(gclassid,sndrmdr=0):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    gclassname = gClassroom.gclassdict['name']

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

    students = gClassroom.groster['roster']

    # This is a list of gids for the students that checked in
    checkingids = [checkin.student.gid for checkin in checkins]

    # This is a list of gids for the students in the Google Classroom
    rostergids = [student['userId'] for student in students]

    # This is a list of gids for of students on the google roster but not in the checked in
    notcheckedingids = [rostergid for rostergid in rostergids if rostergid not in checkingids]

    notcheckedstus = []
    notcheckedstuschoices = []

    for stu in students:
        if stu['userId'] in notcheckedingids:
            try:
                notcheckedstus.append(stu['otdobject'])
            except:
                flash(f"{stu['profile']['name']['fullName']} may not have an account in OTData or you may need to update the roster for this class.")
            else:
                try:
                    notcheckedstuschoices.append((stu['otdobject']['aeriesid'],Markup(f"{stu['sortCohort']}: {stu['otdobject']['lname']}, {stu['otdobject']['fname']} <a href='/profile/{stu['otdobject']['aeriesid']}'>&#128279;</a>")))
                except:
                    notcheckedstuschoices.append((stu['otdobject']['aeriesid'],Markup(f"{stu['otdobject']['lname']}, {stu['otdobject']['fname']} <a href='/profile/{stu['otdobject']['aeriesid']}'>&#128279;</a>")))


    # If there are students who did not checkin get a list of all their user objects

    # sort the list of tuples by its second item which is student's name
    notcheckedstuschoices = sorted(notcheckedstuschoices, key = lambda i: (i[1]))


    # lst = len(notcheckedstuschoices)  
    # for i in range(0, lst):  
    #     for j in range(0, lst-i-1):  
    #         if (notcheckedstuschoices[j][1] > notcheckedstuschoices[j + 1][1]):  
    #             temp = notcheckedstuschoices[j]  
    #             notcheckedstuschoices[j]= notcheckedstuschoices[j + 1]  
    #             notcheckedstuschoices[j + 1]= temp  

    stuForm.student.choices = notcheckedstuschoices

    if request.form and 'submitStuForm' in request.form and len(stuForm.student.data)>0:
        for stu in stuForm.student.data:
            student = User.objects.get(aeriesid=stu)
            checkinstus(gclassid,gclassname,student,searchdatetime)
        request.form = None
        return redirect(url_for('checkinsfor', gclassid=gclassid)) 

    return render_template('checkinsfor.html', querydate= dateForm.querydate.data, checkins=checkins, stuForm=stuForm, dateForm=dateForm, gclassid=gclassid, gclassname=gclassname, notcheckedstus=notcheckedstus, searchdatetime=searchdatetime)

