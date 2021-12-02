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
import matplotlib.pyplot as plt 


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

@app.route('/missingclass/<gclassid>')
def missingclass(gclassid):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)

    #Get all the student submissions
    try:
        subsDF = pd.DataFrame.from_dict(gClassroom.studsubsdict['studsubs'], orient='index')
    except:
        flash(Markup(f'You need to <a href="/getstudsubs/{{gclassid}}">update you info from Google Clasroom.</a>'))
        return redirect(url_for('checkin'))

    subsDF = subsDF.drop('id', 1)

    subsDFlink = subsDF.drop_duplicates(subset=['userId'])
    subsDFlink = subsDFlink[['userId','alternateLink']]
    subsDFlink['missingLink'] = subsDFlink.apply(lambda row: row.alternateLink[0:47]+"/sp"+row.alternateLink[-17:]+"/m", axis=1)

    #Create a list of students
    dictfordf = {}
    for row in gClassroom.groster['roster']:
        newRow = {'userId':row['userId'],'name':row['profile']['name']['fullName'],'email':row['profile']['emailAddress']}
        dictfordf[row['userId']] = newRow

    stusDF = pd.DataFrame.from_dict(dictfordf, orient='index')

    #Merge the students with the assignments
    gbDF = pd.merge(stusDF, 
                      subsDF, 
                      on ='userId', 
                      how ='inner')

    #Get all the assignments
    dictfordf = {}
    for row in gClassroom.courseworkdict['courseWork']:
        dictfordf[row['id']] = row

    courseworkDF = pd.DataFrame.from_dict(dictfordf, orient='index')
    courseworkDF.rename(columns={"id": "courseWorkId"}, inplace=True)

    #merge in all the assignments
    gbDF = pd.merge(courseworkDF, 
                    gbDF, 
                    on ='courseWorkId', 
                    how ='inner')
   
    gbDF = gbDF.drop(['creationTime_x','updateTime_x','dueTime','maxPoints','assignment','assigneeMode','courseId_y','description','materials','submissionModificationMode','creatorUserId','individualStudentsOptions','assignmentSubmission','draftGrade','shortAnswerSubmission'], 1)
    # drop all rows that are NOT late
    gbDF = gbDF.dropna(subset=['late'])
    # drop all rows that are turned_in
    index_names = gbDF[ gbDF['state_y'] == "TURNED_IN" ].index
    gbDF.drop(index_names, inplace = True)
    # drop all rows with a grade including zero
    index_names = gbDF[ gbDF['assignedGrade'] >= 0 ].index
    gbDF.drop(index_names, inplace = True)

    gbDFpivot = pd.pivot_table(data=gbDF,index=['email'],aggfunc={'email':len})

    gbDFpivot.rename(columns={"email": "TotalMissing"}, inplace=True)
    gbDFpivot.reset_index()
    gbDFpivot.rename(columns={"index": "email"}, inplace=True)


    gbDFpivot = pd.merge(stusDF, 
                    gbDFpivot, 
                    on ='email', 
                    how ='inner')

    gbDFpivot = pd.merge(subsDFlink, 
                gbDFpivot, 
                on ='userId', 
                how ='inner')

    gbDFpivot.drop(['alternateLink','userId'],1,inplace=True)

    gbDFpivot = gbDFpivot.sort_values(by=['TotalMissing'], ascending=False)
    gbDFpivot['TotalMissing'] = gbDFpivot.apply(lambda row: f'<a href="{row.missingLink}">{row.TotalMissing}</a>', axis=1)
    gbDFpivot.reset_index(inplace=True)
    gbDFpivot.drop(['index','missingLink','email'],1,inplace=True)


    displayDFHTML = Markup(gbDFpivot.to_html(escape=False))

    return render_template('missingclass.html',gClassroom=gClassroom,displayDFHTML=displayDFHTML)

@app.route('/studsubs/<gclassid>')
def studsubs(gclassid):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)

    try:
        subsDF = pd.DataFrame.from_dict(gClassroom.studsubsdict['studsubs'], orient='index')
    except:
        flash(Markup(f'You need to <a href="/getstudsubs/{{gclassid}}">update you info from Google Clasroom.</a>'))
        return redirect(url_for('checkin'))

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

    gbDF.fillna('', inplace=True)
    gbDF['late'] = gbDF['late'].astype('bool')
    #gbDF.replace("True", 1)
    print(gbDF.dtypes)
    gbDF = pd.pivot_table(data=gbDF,index=['email'],aggfunc={'late':np.sum,'email':len})
    gbDF['On Time %'] = 100-(gbDF['late'] / gbDF['email'] * 100)
    gbDF.rename(columns={"email": "total"}, inplace=True)
    gbDF = gbDF.sort_values(by=['On Time %'], ascending=False)
    median = round(gbDF['On Time %'].median(),2)
    mean = round(gbDF['On Time %'].mean(), 2)

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

    return render_template('studsubs.html',gClassroom=gClassroom,displayDFHTML=displayDFHTML,median=median,mean=mean)


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
    editGClass = currUser.gclasses.get(gclassid = gclassid)
    
    form = GClassForm()

    if form.validate_on_submit():
        currUser.gclasses.filter(gclassid = gclassid).update(
            classname = form.classname.data, 
            status = form.status.data
        )

        currUser.gclasses.filter(gclassid = gclassid).save()
        return redirect(url_for('checkin'))

    if editGClass.classname:
        form.classname.data = editGClass.classname
    else:
        form.classname.data = editGClass.gclassroom.gclassdict['name']
    
    if editGClass.status:
        form.status.data = editGClass.status

    return render_template('editgclass.html', form = form, editGClass = editGClass)

@app.route('/deletegclass/<gclassid>', methods=['GET', 'POST'])
def deletegclass(gclassid):
    currUser = User.objects.get(pk=session['currUserId'])
    currUser.gclasses.filter(gclassid = gclassid).delete()
    currUser.gclasses.filter(gclassid = gclassid).save()

    return redirect(url_for('checkin'))
