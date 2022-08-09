import matplotlib

from app.routes.coursecat import course
matplotlib.use('Agg')
import matplotlib.pyplot as plt 
from app import app
from .users import credentials_to_dict
from flask import render_template, redirect, session, flash, url_for, Markup, render_template_string
from app.classes.data import GEnrollment, StudentSubmission, User, GoogleClassroom
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
        gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    except Exception as error:
        flash(f"Got an error: {error}")
        flash(f"Could not find this class in list of Google Classrooms at OTData.")
        return redirect(url_for('roster',gclassid=gclassid))
    else:
        try:
            stu.gclasses.get(gclassid=gclassid)
        except mongoengine.errors.DoesNotExist:
            stu.gclasses.create(
                gclassid=gclassid,
                gclassroom = gClassroom
                )
            stu.save()
        else:
            flash(f"{stu.fname} {stu.lname} already has this class stored in OTData.")
            return redirect(url_for('roster',gclassid=gclassid))

    flash(f"This class has been added to the OTData classes for {stu.fname} {stu.lname}.")
    
    return redirect(url_for('roster',gclassid=gclassid))

@app.route('/student/getstudentwork/<gclassid>')
def getstudentwork(gclassid):
    if session['role'].lower() != "student":
        flash('This link is only for students.')
        return redirect('checkin')

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
        counter=counter+1
        if not pageToken:
            break
    studSubsDict = {}
    studSubsDict['mySubmissions'] = studSubsAll
    currUser = User.objects.get(gid=session['gid'])
    currUser.gclasses.filter(gclassid = gclassid).update(
        submissions = studSubsDict,
        submissionsupdate = dt.datetime.utcnow()
    )
    currUser.save()

    return redirect(url_for('checkin'))

@app.route('/student/mywork')
def mywork():
    currUser = User.objects.get(gid = session['gid'])

    myClasses = currUser.gclasses.filter(status = 'Active')
    myWorkList= []
    courseWorkAll = []
    classList = []
    for myClass in myClasses:
        myWorkList = myWorkList + myClass.submissions['mySubmissions']
        if not myClass.gclassroom.courseworkdict or myClass.gclassroom.courseworkupdate - dt.timedelta(1) > dt.datetime.utcnow():
            courseWork = getCourseWork(myClass.gclassid)
            if courseWork == "refresh":
                return redirect(url_for('authorize'))
        else:
            courseWork = myClass.gclassroom.courseworkdict

        thisClass = {'className':myClass.gclassroom.gclassdict['name'],'courseId':myClass.gclassroom.gclassdict['id']}
        classList.append(thisClass)
        courseWorkAll = courseWorkAll + courseWork['courseWork']
        
    myWorkDF = pd.DataFrame(myWorkList)
    courseWorkDF = pd.DataFrame(courseWorkAll)
    courseWorkDF.rename(columns={"id": "courseWorkId"}, inplace=True)
    classListDF = pd.DataFrame(classList)

    #merge in all the assignments
    myWorkDF = pd.merge(courseWorkDF, 
                    myWorkDF, 
                    on ='courseWorkId', 
                    how ='inner')

    myWorkDF.rename(columns={"courseId_x": "courseId"}, inplace=True)

    #merge in all the assignments
    myWorkDF = pd.merge(classListDF, 
                    myWorkDF, 
                    on ='courseId', 
                    how ='inner')


    myWorkDF.drop(['materials','state_x','creationTime_x','updateTime_x','workType','submissionModificationMode','creatorUserId','topicId','dueTime','multipleChoiceQuestion','courseId_y','userId','courseWorkType','assignmentSubmission','shortAnswerSubmission','multipleChoiceSubmission'],1,inplace=True)

    displayDFHTML = Markup(myWorkDF.to_html(escape=False))
    
    return render_template('mywork.html',displayDFHTML=displayDFHTML)


@app.route('/ontimeperc/<gclassid>')
def ontimeperc(gclassid):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    enrollments = GEnrollment.objects(gclassroom=gClassroom)
    if len(enrollments) < 2:
        flash("There's no students in your roster.  You need to update your roster")
        return redirect(url_for('roster',gclassid=gclassid))

    try:
        subsDF = pd.DataFrame.from_dict(gClassroom.studsubsdict['studsubs'], orient='index')
    except:
        flash(Markup(f'You need to <a href="/getstudsubs/{gclassid}">update student submissions.</a>'))
        return redirect(url_for('gclass',gclassid=gclassid))

    subsDF = subsDF.drop(columns='id')

    subsDF = subsDF[['userId', 'courseId', 'courseWorkId', 'creationTime', 'updateTime', 'state', 'alternateLink', 'courseWorkType', 'assignmentSubmission', 'submissionHistory', 'late', 'draftGrade', 'assignedGrade']]

    dictfordf = {}
    for row in enrollments:
        newRow = {'userId':row['owner']['gid'],'fname':row['owner']['fname'],'lname':row['owner']['lname'],'email':row['owner']['otemail']}
        dictfordf[row['owner']['id']] = newRow

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
    gbDF.fillna('', inplace=True)
    gbDF['late'] = gbDF['late'].astype('bool')
    gbDF = pd.pivot_table(data=gbDF,index=['email'],aggfunc={'late':np.sum,'email':len})
    gbDF['On Time %'] = 100-(gbDF['late'] / gbDF['email'] * 100)
    gbDF.rename(columns={"email": "total"}, inplace=True)
    gbDF = gbDF.sort_values(by=['On Time %'], ascending=False)
    median = round(gbDF['On Time %'].median(),2)
    mean = round(gbDF['On Time %'].mean(), 2)

    stuList = gbDF.reset_index(level=0)
    stuList = stuList.values.tolist()

    # mmerge table code
    mmerge='<table><tr><th>ID</th><th>StudentName</th><th>StudentEmail</th><th>Emails</th><th>NumMissing</th></tr>'
    for stu in stuList:
        mmerge+='<tr>'
        emails=""
        email=stu[0].strip()
        missing = stu[2]
        
        try:
            stu = User.objects.get(otemail=email)
        except:
            if len(email)>1:
                flash( f"couldn't find {email} in our records")
        mmerge+=f"<td>{stu.aeriesid}</td><td>{stu.fname} {stu.lname}</td><td>{email}</td>"
        emails+=f"{email}"

        if stu.aadultemail:
            emails+=f", {stu.aadultemail};"

        for adult in stu.adults:
            if adult.email:
                if stu.aadultemail and adult.email != stu.aadultemail:
                    emails+=f", {adult.email};"
                elif not stu.aadultemail:
                    emails+=f", {adult.email};"

        mmerge+=f"<td>{emails}</td><td>{missing}</td>"
        mmerge+='</tr>'
    mmerge+="</table>"
    parents=Markup(render_template_string(mmerge))


    #plotting boxplot 
    #plt.boxplot([x for x in gbDF['On Time %']],labels=[x for x in gbDF.index], showmeans=True) 
    plt.boxplot([x for x in gbDF['On Time %']], showmeans=True) 

    #x and y-axis labels 
    plt.xlabel('name') 
    plt.ylabel('%') 

    #plot title 
    plt.title('Analysing on time %') 

    #save and display 
    plt.savefig(f'app/static/{gclassid}.png',dpi=300,bbox_inches='tight')
    plt.clf()
  
    displayDFHTML = Markup(pd.DataFrame.to_html(gbDF))
    #displayDFHTML = Markup(pd.DataFrame.to_html(courseworkDF))
    #stusDFHTML = Markup(pd.DataFrame.to_html(stusDF))
    #subsDFHTML = Markup(pd.DataFrame.to_html(subsDF))

    return render_template('studsubs.html',gClassroom=gClassroom,parents=parents,displayDFHTML=displayDFHTML,median=median,mean=mean)

def getStudSubs(gclassid,courseWorkId="-"):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    # setup the Google API access credentials
    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        flash('Had to reauthorize your Google credentials.')
        return "refresh"
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
                courseWorkId=courseWorkId,
                pageToken=pageToken
                ).execute()
        except RefreshError:
            flash('Had to reauthorize your Google credentials.')
            return "refresh"

        except Exception as error:
            flash(f'Unknown error: {error}')
            return "Refresh"

        studSubsAll.extend(studSubs['studentSubmissions'])
        pageToken = studSubs.get('nextPageToken')
        counter=counter+1
        if not pageToken:
            break
    
    subsLength = len(studSubsAll)
    for i,sub in enumerate(studSubsAll):
        newSub = StudentSubmission(
            stugid = sub['userId'],
            gclassroom = gClassroom,
            studsubid = sub['id'],
            studsubdict = sub,
            lastupdate = dt.datetime.utcnow()
        )
        notSaved = 0
        try:
            newSub.save()
        except mongoengine.errors.NotUniqueError:
            pass


    dictfordf = {}
    for row in studSubsAll:
        dictfordf[row['id']] = row

    studSubsAll = {'lastUpdate':dt.datetime.utcnow(),'studsubs':dictfordf}
    gClassroom.update(
        studsubsdict = studSubsAll
    )

    return studSubsAll

@app.route('/getstudsubs/<gclassid>/<courseWorkId>')
@app.route('/getstudsubs/<gclassid>')
def getstudsubs(gclassid,courseWorkId="-"):

    courseWork = getCourseWork(gclassid)
    if courseWork == "refresh":
        return redirect(url_for('authorize'))
    elif courseWork == False:
        return redirect(url_for('checkin'))

    studSubsAll = getStudSubs(gclassid,courseWorkId)
    if studSubsAll == "refresh":
        return redirect(url_for('authorize'))

    return redirect(url_for('ontimeperc',gclassid=gclassid))

## Replicated in sbg.py as gclasslist
# this function exists to update the stored values for one or more google classrooms
@app.route('/gclasses')
def gclasses(gclassid=None):

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
    for i,gCourse in enumerate(gCourses):
        length = len(gCourses)
        print(f"course {i}/{length}")
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
            ).save()

        # If there is NOT a teacher in OTData and NOT a course in OTData
        elif not otdataGCourse and not otdataGClassTeacher:
            otdataGCourse = GoogleClassroom(
                gclassdict = gCourse,
                gteacherdict = GClassTeacher,
                gclassid = gCourse['id']
            ).save()

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

        # check to see if the class exists in the current user's embedded doc
        try:
            userGClass = currUser.gclasses.get(gclassid=gCourse['id'])
        except:
            userGClass = None

        # if the class does not exist then add it to the embedded doc 
        if not userGClass:
            newUserGClass = currUser.gclasses.create(
                gclassid = gCourse['id'],
                gclassroom = otdataGCourse,
                classname = otdataGCourse.gclassdict['name'],
                status = 'Inactive'
            )
            userGClass = newUserGClass

    currUser.save()

    return redirect(url_for('checkin'))

@app.route('/editgclass/<gclassid>', methods=['GET', 'POST'])
def editgclass(gclassid):
    currUser = User.objects.get(pk=session['currUserId'])
    gclassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    enrollment = GEnrollment.objects.get(owner=currUser,gclassroom=gclassroom)
    
    form = GClassForm()

    if form.validate_on_submit():
        enrollment.update(
            classnameByUser = form.classname.data, 
            status = form.status.data
        )

        return redirect(url_for('checkin'))

    if enrollment.classnameByUser:
        form.classname.data = enrollment.classnameByUser
    else:
        form.classname.data = enrollment.gclassroom.gclassdict['name']
    
    if enrollment.status:
        form.status.data = enrollment.status

    return render_template('editgclass.html', form = form, editGClass = enrollment)

@app.route('/deletegclass/<gclassid>', methods=['GET', 'POST'])
def deletegclass(gclassid):
    
    if session['role'].lower() == "student":
        flash("Students can't delete enrollments.")
    else:
        currUser = User.objects.get(pk=session['currUserId'])
        gclassroom = GoogleClassroom.objects.get(gclassid=gclassid)
        enrollment = GEnrollment.objects.get(owner=currUser,gclassroom=gclassroom)
        enrollment.delete()
        flash("deleted")
    
    return redirect(url_for('checkin'))
