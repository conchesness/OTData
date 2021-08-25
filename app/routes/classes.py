from app import app
from .users import credentials_to_dict
from flask import render_template, redirect, session, flash, url_for
from app.classes.data import User, GoogleClassroom
from app.classes.forms import GClassForm
import mongoengine.errors
import google.oauth2.credentials
import googleapiclient.discovery
from google.auth.exceptions import RefreshError

@app.route('/addgclass/<gmail>/<gclassid>/<gclassname>')
def addgclass(gmail,gclassid,gclassname):

    try:
        stu = User.objects.get(otemail=gmail)
    except Exception as error:
        flash(f"Got an error: {error}")
        flash("I can't find this user in OTData.")
        return redirect(url_for('roster',gclassid=gclassid, gclassname=gclassname))
    
    try:
        stu.gclasses.get(gclassid=gclassid)
    except mongoengine.errors.DoesNotExist:
        pass
    else:
        flash(f"{stu.fname} {stu.lname} already has {gclassname} stored in OTData.")
        return redirect(url_for('roster',gclassid=gclassid, gclassname=gclassname))
    
    try:
        gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    except Exception as error:
        flash(f"Got an error: {error}")
        flash(f"Could not find {gclassname} in list of Google Classrooms at OTData.")
        return redirect(url_for('roster',gclassid=gclassid, gclassname=gclassname))
    else:
        stu.gclasses.create(
            gclassid=gclassid,
            gclassroom = gClassroom
            )
        stu.save()
        flash(f"{gclassname} has been added to the OTData classes for {stu.fname} {stu.lname}.")

    return redirect(url_for('roster',gclassid=gclassid, gclassname=gclassname))

# this function exists to update the stored values for one or more google classrooms
@app.route('/gclasses/<gclassid>')
@app.route('/gclasses')
def gclasses(gclassid=None):
    if gclassid:
        gclassid=str(gclassid)

    # Get the currently logged in user because, this will only work for the Current User as I don't have privleges to retrieve classes for other people.
    currUser = User.objects.get(pk = session['currUserId'])
    # setup the Google API access credentials
    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')
    session['credentials'] = credentials_to_dict(credentials)
    classroom_service = googleapiclient.discovery.build('classroom', 'v1', credentials=credentials)

    # retrieve one Google Class from Google if the class id is passed in the url
    if gclassid:
        gCourses = []
        try:
            gCourse = classroom_service.courses().get(id=gclassid).execute()
        except RefreshError:
            flash("When I asked for the courses from Google Classroom I found that your credentials needed to be refreshed.")
            return redirect('/authorize')
        
        gCourses.append(gCourse)

    # Get all of the google classes if there is not a class id in the url
    # put the one class in an array of one item so it works in the following for loop
    else:
        try:
            gCourses = classroom_service.courses().list(courseStates='ACTIVE').execute()
            gCourse = None
            gCourses = gCourses['courses']
        except RefreshError:
            flash("When I asked for the courses from Google Classroom I found that your credentials needed to be refreshed.")
            return redirect('/authorize')

    # This will be a list of all the OTData GoogleClassroom objects for this query
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

        # if the GCourse IS NOT in OTData the teacher IS in the OTData
        if not otdataGCourse and otdataGClassTeacher:
            otdataGCourse = GoogleClassroom(
                gclassdict = gCourse,
                gteacherdict = GClassTeacher,
                gclassid = gCourse['id'],
                teacher = otdataGClassTeacher
            ).save()

        # If there is a teacher in OTData and not a gcourse
        elif not otdataGCourse and not otdataGClassTeacher:
            otdataGCourse = GoogleClassroom(
                gclassdict = gCourse,
                gteacherdict = GClassTeacher,
                gclassid = gCourse['id']
            ).save()
        # if the GCourse is in OTData then update it
        elif otdataGCourse and otdataGClassTeacher:
            otdataGCourse.update(
                gclassdict = gCourse,
                gteacherdict = GClassTeacher,
                teacher = otdataGClassTeacher
            )
        elif otdataGCourse and not otdataGClassTeacher:
            otdataGCourse.update(
                gclassdict = gCourse,
                gteacherdict = GClassTeacher
            )

        # check to see if the class exists in the user's embedded doc
        try:
            userGClass = currUser.gclasses.get(gclassid=gCourse['id'])
        except:
            userGClass = None

        # if the class does not exist then add it to the embedded doc
        if not userGClass:
            newUserGClass = currUser.gclasses.create(
                gclassid = gCourse['id'],
                gclassroom = otdataGCourse
            )
            userGClass = newUserGClass
        else:
            userGClass = currUser.gclasses.filter(gclassid=gCourse['id']).update(gclassroom = otdataGCourse)
        
    currUser.save()

    return redirect(url_for('checkin'))

@app.route('/editgclass/<gclassid>', methods=['GET', 'POST'])
def editgclass(gclassid):
    currUser = User.objects.get(pk=session['currUserId'])
    editGClass = currUser.gclasses.get(gclassid = gclassid)
    
    form = GClassForm()

    if form.validate_on_submit():

        currUser.gclasses.filter(gclassid = gclassid).update(
            classname = form.classname.data,
            status = form.status.data
        )

        currUser.gclasses.filter(gclassid = gclassid).save()
        return redirect(url_for('checkin'))

    # if editGClass.classname:
    #     form.classname.data = editGClass.classname

    return render_template('editgclass.html', form = form, editGClass = editGClass)

@app.route('/deletegclass/<gclassid>', methods=['GET', 'POST'])
def deletegclass(gclassid):
    currUser = User.objects.get(pk=session['currUserId'])
    currUser.gclasses.filter(gclassid = gclassid).delete()
    currUser.gclasses.filter(gclassid = gclassid).save()

    return redirect(url_for('checkin'))
