from app import app
from flask import render_template, redirect, session, flash, url_for, Markup, render_template_string
from app.classes.data import User, GoogleClassroom, GEnrollment, CourseWork, Standard
from app.classes.forms import AssignmentForm, StandardForm
import mongoengine.errors
import google.oauth2.credentials
import googleapiclient.discovery
from google.auth.exceptions import RefreshError
import datetime as dt
from .users import credentials_to_dict
#from .roster import getCourseWork

# this function exists to update or create active google classrooms for the current user
# Teacher or student
@app.route('/getgclasses')
def getgclasses():

    # Get the currently logged in user because, this will only work for the Current User as I don't have privleges to retrieve classes for other people.
    currUser = User.objects.get(pk = session['currUserId'])
    # setup the Google API access credentials
    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')
    session['credentials'] = credentials_to_dict(credentials)
    classroom_service = googleapiclient.discovery.build('classroom', 'v1', credentials=credentials)

    # Get all of the google classes
    try:
        gCourses = classroom_service.courses().list(courseStates='ACTIVE').execute()
    except RefreshError:
        flash("When I asked for the courses from Google Classroom I found that your credentials needed to be refreshed.")
        return redirect('/authorize')
    else:
        gCourse = None
        gCourses = gCourses['courses']

    # Iterate through the classes
    for gCourse in gCourses:
        # get the teacher record
        try:
            # See if I can find a Google Teacher User
            GClassTeacher = classroom_service.userProfiles().get(userId=gCourse['ownerId']).execute()
        except:
            GClassTeacher = None

        # See if the teacher has a record on OTData site
        try:
            otdataGClassTeacher = User.objects.get(gid = gCourse['ownerId'])
        except:
            otdataGClassTeacher = None

        # Check to see if this course is saved in OTData
        try:
            otdataGCourse = GoogleClassroom.objects.get(gclassid = gCourse['id'])
        except:
            otdataGCourse = None

        # if the GCourse IS NOT in OTData and the teacher IS in the OTData
        if not otdataGCourse and otdataGClassTeacher:
            otdataGCourse = GoogleClassroom(
                gclassdict = gCourse,
                gteacherdict = GClassTeacher,
                gclassid = gCourse['id'],
                teacher = otdataGClassTeacher
            )
            otdataGCourse.save()

        # If there is NOT a teacher in OTData and NOT a course in OTData
        elif not otdataGCourse and not otdataGClassTeacher:
            otdataGCourse = GoogleClassroom(
                gclassdict = gCourse,
                gteacherdict = GClassTeacher,
                gclassid = gCourse['id']
            )
            otdataGCourse.save()

        # if the GCourse and the teacher is in OTData then update it
        elif otdataGCourse and otdataGClassTeacher:
            otdataGCourse.update(
                gclassdict = gCourse,
                gteacherdict = GClassTeacher,
                teacher = otdataGClassTeacher
            )

        # if the course is in OTData but the teacher is not in otdata
        elif otdataGCourse and not otdataGClassTeacher:
            otdataGCourse.update(
                gclassdict = gCourse,
                gteacherdict = GClassTeacher
            )

        # Check for an enrollment.  If not there, create one.
        try:
            userEnrollment = GEnrollment.objects.get(owner = currUser, gclassroom = otdataGCourse)
        except:
            userEnrollment = GEnrollment(
                owner = currUser, 
                gclassroom = otdataGCourse)
            userEnrollment.save()

    return redirect(url_for('checkin'))

@app.route('/gclass/<gclassid>')
def gclass(gclassid):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    enrollments = GEnrollment.objects(gclassroom=gClassroom)
    gCourseWork = CourseWork.objects(gclassroom = gClassroom)
    return render_template('sbg/gclass.html', gclass=gClassroom, enrollments=enrollments, gCourseWork = gCourseWork)

@app.route('/gclass/assignments/<gclassid>')
def gClassAssignments(gclassid):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    asses = CourseWork.objects(gclassroom=gClassroom)
    asses = sorted(asses, key = lambda i: (i.courseworkdict['title']))
    return render_template('sbg/assignments.html', gClass=gClassroom, asses = asses)

@app.route('/assignment/<assid>', methods=['GET', 'POST'])
def gAss(assid):
    ass = CourseWork.objects.get(id=assid)
    standards = Standard.objects()
    standardsChoices = []
    for standard in standards:
        standardsChoices.append((standard.id,standard.name))
    form = AssignmentForm()
    form.standards.choices = standardsChoices
    if form.is_submitted():
        ass.update(
            standards = []
        )
        ass.update(
            add_to_set__standards=form.standards.data
        )
        ass.reload()
    return render_template('sbg/assignment.html',ass=ass, form=form)


@app.route('/standard/list', methods=['GET', 'POST'])
def standardlist():
    form = StandardForm()
    standards = Standard.objects()
    return render_template('sbg/standards.html',standards=standards,form=form)

@app.route('/standard/new', methods=['GET', 'POST'])
def standardNew():
    form = StandardForm()
    if form.validate_on_submit():
        standardNew = Standard(
            name = form.name.data,
            desc = form.desc.data,
            gclass = form.gclass.data
        )
        standardNew.save()
        return redirect(url_for('standardlist'))
    if session['role'].lower() == 'teacher':
        currTeacher = User.objects.get(gid = session['gid'])
    myGClasses = GoogleClassroom.objects(teacher=currTeacher)
    gClassChoices = []
    for gClass in myGClasses:
        gClassChoices.append((gClass.id,gClass.gclassdict['name']))
    form.gclass.choices = gClassChoices
    return render_template('sbg/standardform.html', form=form)

@app.route('/standard/edit/<standardid>', methods=['GET', 'POST'])
def standardedit(standardid):
    form = StandardForm()
    standardEdit = Standard.objects.get(id = standardid)
    if form.validate_on_submit():
        standardEdit.update(
            name = form.name.data,
            desc = form.desc.data
            )
        return redirect(url_for('standardlist'))
    if session['role'].lower() == 'teacher':
        currTeacher = User.objects.get(gid = session['gid'])
    myGClasses = GoogleClassroom.objects(teacher=currTeacher)
    gClassChoices = []
    for gClass in myGClasses:
        gClassChoices.append((gClass.id,gClass.gclassdict['name']))
    form.gclass.choices = gClassChoices
    form.gclass.data = standardEdit.gclass
    form.name.data = standardEdit.name
    form.desc.data = standardEdit.desc
    return render_template('sbg/standardform.html',form=form)

@app.route('/standard/delete/<standardid>')
def standardDelete(standardid):
    standardDel = Standard.objects.get(id=standardid)
    standardDel.delete()
    flash('Standard is deleted.')
    return redirect(url_for('standardlist'))


## Scripts
# unset sections from the User document

# to run this script you have to add 'sections' and 'enrollments' 
# temporarily to the User class in data.py
@app.route('/unsetfieldsfromuser')
def unsetfieldsfromuser():
    users = User.objects()
    for i,user in enumerate(users):
        try:
            user.update(unset__sections = 1)
        except:
            print(f"{i}: no sections on {user.fname}")
        else:
            print(f"{i}: deleted sections from  {user.fname}")

        try:
            user.update(unset__enrollments = 1)
        except:
            print(f"{i}: no enrollments on {user.fname}")
        else:
            print(f"{i}: deleted enrollments from  {user.fname}")

        try:
            user.update(unset__gclasses = 1)
        except:
            print(f"{i}: no gclasses on {user.fname}")
        else:
            print(f"{i}: deleted gclasses from  {user.fname}")

    return redirect(url_for('index'))

@app.route('/unsetfieldsfromgoogleclassroom')
def unsetgrosterfromgoogleclassroom():
    gclassrooms = GoogleClassroom.objects()
    length = len(gclassrooms)
    for i,gclassroom in enumerate(gclassrooms):

        try:
            gclassroom.groster
        except:
            #print(f"{i}/{length}: no groster")
            pass
        else:
            gclassroom.update(unset__groster = 1)
            #print(f"{i}/{length}: deleted groster")

        if gclassroom.gteacherdict and not gclassroom.teacher:

            try:
                teacher = User.objects.get(otemail = str(gclassroom.gteacherdict['emailAddress']))
            except:
                print("No teacher added")
            else:
                gclassroom.update(teacher = teacher)
                print('teacher added')

    return redirect(url_for('index'))

@app.route('/scriptsforenrollments')
def scriptsforenrollments():
    enrollments = GEnrollment.objects()
    for enrollment in enrollments:
        print(enrollment.status)
        if not enrollment.status:
            enrollment.update(status='--')
            print('yup')
    return redirect(url_for('index'))