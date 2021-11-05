from app import app
from .users import credentials_to_dict
from flask import render_template, redirect, session, flash, url_for, Markup
from app.classes.data import User, GoogleClassroom
from app.classes.forms import GClassForm
import mongoengine.errors
import google.oauth2.credentials
import googleapiclient.discovery
from google.auth.exceptions import RefreshError
import datetime as dt
from .roster import getCourseWork
import pandas as pd
import numpy as np

@app.route('/addgclass/<gmail>/<gclassid>')
def addgclass(gmail,gclassid):

    try:
        stu = User.objects.get(otemail=gmail)
    except Exception as error:
        flash(f"Got an error: {error}")
        flash("I can't find this user in OTData.")
        return redirect(url_for('roster',gclassid=gclassid))
    
    try:
        stu.gclasses.get(gclassid=gclassid)
    except mongoengine.errors.DoesNotExist:
        pass
    else:
        flash(f"{stu.fname} {stu.lname} already has this class stored in OTData.")
        return redirect(url_for('roster',gclassid=gclassid))
    
    try:
        gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    except Exception as error:
        flash(f"Got an error: {error}")
        flash(f"Could not find this class in list of Google Classrooms at OTData.")
        return redirect(url_for('roster',gclassid=gclassid))
    else:
        stu.gclasses.create(
            gclassid=gclassid,
            gclassroom = gClassroom
            )
        stu.save()
        flash(f"This class has been added to the OTData classes for {stu.fname} {stu.lname}.")

    return redirect(url_for('roster',gclassid=gclassid))

@app.route('/studsubs/<gclassid>')
def studsubs(gclassid):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)

    subsDF = pd.DataFrame.from_dict(gClassroom.studsubsdict['studsubs'], orient='index')
    subsDF = subsDF.drop('id', 1)

    dictfordf = {}
    for row in gClassroom.groster['roster']:
        newRow = {'userId':row['userId'],'name':row['profile']['name']['fullName'],'email':row['profile']['emailAddress']}
        dictfordf[row['userId']] = newRow

    stusDF = pd.DataFrame.from_dict(dictfordf, orient='index')

    gbDF = pd.merge(stusDF, 
                      subsDF, 
                      on ='userId', 
                      how ='inner')

    dictfordf = {}
    for row in gClassroom.courseworkdict['courseWork']:
        dictfordf[row['id']] = row

    courseworkDF = pd.DataFrame.from_dict(dictfordf, orient='index')
    courseworkDF.rename(columns={"id": "courseWorkId"}, inplace=True)

    gbDF = pd.merge(courseworkDF, 
                    gbDF, 
                    on ='courseWorkId', 
                    how ='inner')

    # gbDF = gbDF.drop(
    #     [
    #         'courseId_x',
    #         'courseWorkId',
    #         'description',
    #         'state_x',
    #         'alternateLink_x',
    #         'submissionModificationMode',	
    #         'assigneeMode',
    #         'creatorUserId',
    #         'materials',	
    #         'individualStudentsOptions',
    #         #'multipleChoiceQuestion',	
    #         'courseId_y',	
    #         'creationTime_y',	
    #         'updateTime_y',	
    #         'alternateLink_y',	
    #         'assignmentSubmission',	
    #         'shortAnswerSubmission',	
    #         #'multipleChoiceSubmission',	
    #         'draftGrade',
    #         'creationTime_x',	
    #         'updateTime_x',
    #         'assignment'
    #     ], 1)

    #gbDF = pd.pivot_table(data=gbDF,index=['name'],aggfunc={'late':(lambda x:len(x.unique()))})
    gbDF.fillna('', inplace=True)
    gbDF['late'] = gbDF['late'].astype('bool')
    #gbDF.replace("True", 1)
    print(gbDF.dtypes)
    gbDF = pd.pivot_table(data=gbDF,index=['name'],aggfunc={'late':np.sum,'email':len})
    gbDF['On Time %'] = 100-(gbDF['late'] / gbDF['email'] * 100)
    gbDF.rename(columns={"email": "total"}, inplace=True)
    gbDF = gbDF.sort_values(by=['On Time %'], ascending=False)

    displayDFHTML = Markup(pd.DataFrame.to_html(gbDF))
    #displayDFHTML = Markup(pd.DataFrame.to_html(courseworkDF))
    #stusDFHTML = Markup(pd.DataFrame.to_html(stusDF))
    #subsDFHTML = Markup(pd.DataFrame.to_html(subsDF))

    return render_template('studsubs.html',gClassroom=gClassroom,displayDFHTML=displayDFHTML)


@app.route('/getstudsubs/<gclassid>')
def getstudsubs(gclassid):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    # setup the Google API access credentials
    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')
    session['credentials'] = credentials_to_dict(credentials)
    classroom_service = googleapiclient.discovery.build('classroom', 'v1', credentials=credentials)
    studSubsAll = []
    pageToken=None
    counter=1
    while True:

        try:
            studSubs = classroom_service.courses().courseWork().studentSubmissions().list(
                courseId=gclassid,
                #states=['TURNED_IN','RETURNED','RECLAIMED_BY_STUDENT'],
                courseWorkId='-',
                pageToken=pageToken
                ).execute()
        except RefreshError:
            flash('Had to reauthorize your Google credentials.')
            return redirect('/authorize')

        except Exception as error:
            print(error)

        studSubsAll.extend(studSubs['studentSubmissions'])
        pageToken = studSubs.get('nextPageToken')
        print(counter)
        counter=counter+1
        if not pageToken:
            break

    dictfordf = {}
    for row in studSubsAll:
        dictfordf[row['id']] = row

    studSubsAll = {'lastUpdate':dt.datetime.utcnow(),'studsubs':dictfordf}
    gClassroom.update(
        studsubsdict = studSubsAll
    )

    getCourseWork(gclassid)

    gClassroom.reload()

    return redirect(url_for('studsubs',gclassid=gclassid))


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
        except RefreshError:
            flash("When I asked for the courses from Google Classroom I found that your credentials needed to be refreshed.")
            return redirect('/authorize')
        else:
            gCourse = None
            gCourses = gCourses['courses']

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
