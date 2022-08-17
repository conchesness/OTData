from re import S
from app import app
from app.routes.sbg import gclass
from .users import credentials_to_dict
from flask import render_template, redirect, session, flash, url_for, Markup
from app.classes.data import Course, User, GoogleClassroom, GEnrollment, CourseWork
from app.classes.forms import SimpleForm, SortOrderCohortForm
from datetime import datetime as dt
import mongoengine.errors
import google.oauth2.credentials
import googleapiclient.discovery
from google.auth.exceptions import RefreshError
import ast

# This function retreives all the assignments from Google and stores them in a dictionary
# field on the GoogleClassroom record in the database. 
def getCourseWork(gclassid):
    pageToken = None
    assignmentsAll = {}
    assignmentsAll['courseWork'] = []

    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        flash("need to refresh your connection to Google Classroom.")
        return "refresh"
        # return redirect('/authorize')    
    
    session['credentials'] = credentials_to_dict(credentials)
    classroom_service = googleapiclient.discovery.build('classroom', 'v1', credentials=credentials)
    try:
        topics = classroom_service.courses().topics().list(
            courseId=gclassid
            ).execute()
    except RefreshError:
        return "refresh"
    except Exception as error:
        x, y = error.args     # unpack args
        if isinstance(y, bytes):
            y = y.decode("UTF-8")
        errorDict = ast.literal_eval(y)
        if errorDict['error'] == 'invalid_grant':
            flash('Your login has expired. You need to re-login.')
            return "refresh"
        elif errorDict['error']['status'] == "PERMISSION_DENIED":
            flash("You do not have permission to get assignments from Google for this class.")
            return "refresh"
        else:
            flash(f"Got unknown Error: {errorDict}")
            return False
    
    topics = topics['topic']

    # Topic dictionary
    # [{'courseId': '450501150888', 'topicId': '487477497511', 'name': 'Dual Enrollment', 'updateTime': '2022-05-20T20:55:41.926Z'}, {...}]

    # TODO get all assignments and add as dict to gclassroom record
    while True:
        try:
            assignments = classroom_service.courses().courseWork().list(
                    courseId=gclassid,
                    pageToken=pageToken,
                    ).execute()
        except RefreshError:
            return "refresh"
        except Exception as error:
            x, y = error.args     # unpack args
            if isinstance(y, bytes):
                y = y.decode("UTF-8")
            errorDict = ast.literal_eval(y)
            if errorDict['error'] == 'invalid_grant':
                flash('Your login has expired. You need to re-login.')
                return "refresh"
            elif errorDict['error']['status'] == "PERMISSION_DENIED":
                return "refresh"
            else:
                flash(f"Got unknown Error: {errorDict}")
                return False

        try: 
            assignmentsAll['courseWork'].extend(assignments['courseWork'])
        except (KeyError,UnboundLocalError):
            break
        else:
            pageToken = assignments.get('nextPageToken')
            if pageToken == None:
                break

    for ass in assignmentsAll['courseWork']:
        for topic in topics:
            try:
                ass['topicId']
            except:
                ass['topicId'] = None
            if topic['topicId'] == ass['topicId']:
                ass['topic'] = topic['name']
                break

        
    gclassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    gclassroom.update(courseworkdict = assignmentsAll, courseworkupdate = dt.utcnow())
    return assignmentsAll


@app.route("/roster/<gclassid>", methods=['GET','POST'])
def roster(gclassid):
    
    gclassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    otdstus = None

    try:
        enrollments = GEnrollment.objects(gclassroom = gclassroom)
    except:
        flash(Markup(f"You need to <a href='/getroster/{gclassid}'>update your roster from Google Classroom</a>."))
        return redirect(url_for('checkin'))

    otdstus = []
    for enrollment in enrollments:
        if enrollment.owner.role.lower() == 'student' and enrollment.owner.lname and enrollment.owner.fname:
            otdstus.append(enrollment)
        elif enrollment.owner.role.lower() == 'student':
            flash(f"Something's wrong with this students record so they were not included in the roster.: {enrollment.owner.otemail}")
    try:
        otdstus = sorted(otdstus, key = lambda i: (i.sortCohort,i.owner.lname,i.owner.fname))
    except Exception as error:
        flash(f"Sort failed in the roster route with error: {error}")

    return render_template('rosternew.html',gclassname=gclassroom.gclassdict['name'], gclassid=gclassid, otdstus=otdstus)

@app.route("/getroster/<gclassid>/<index>", methods=['GET','POST'])
@app.route("/getroster/<gclassid>", methods=['GET','POST'])
def getroster(gclassid,index=0):
    
    index=int(index)
    
    # Get the Google Classroom from OTData
    try:
        currGClass = GoogleClassroom.objects.get(gclassid=gclassid)
    except:
        flash(f"There is no Google Classroom with the id {gclassid}")
        return redirect(url_for('gclasslist'))

    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')    
    session['credentials'] = credentials_to_dict(credentials)
    classroom_service = googleapiclient.discovery.build('classroom', 'v1', credentials=credentials)

    # If the index is 0 then we are at the begining of the process and need to 
    # get the roster from Google
    if index == 0:
        session['missingStus'] = []
        currGClass.update(
            grosterTemp = []
            )
        gstudents = []
        pageToken = None
        try:
            students_results = classroom_service.courses().students().list(courseId = gclassid,pageToken=pageToken).execute()
        except RefreshError:
            flash("When I asked for the courses from Google Classroom I found that your credentials needed to be refreshed.")
            return redirect('/authorize')
        
        while True:
            pageToken = students_results.get('nextPageToken')
            gstudents.extend(students_results['students'])
            if not pageToken:
                break
            students_results = classroom_service.courses().students().list(courseId = gclassid,pageToken=pageToken).execute()
        
        studentsOnly=[]
        for student in gstudents:
            if student['profile']['emailAddress'][:2] == 's_':
                studentsOnly.append(student)
        gstudents = studentsOnly

    # if the Index is at something other than 0 then we need retrieve the roster that is in progress 
    # from OTDATA
    else:
        gstudents = currGClass.grosterTemp

    numStus = len(gstudents)
    # the number of students that will be processed on each iteration
    numIterations = 3
    # The iterator starts at zero and is incremented until it matches the # of iterations
    iterator = 0
    
    for stu in gstudents[index:]:

        try:
            # see if they are in OTData
            otdstu = User.objects.get(otemail=stu['profile']['emailAddress'])
        except mongoengine.errors.DoesNotExist as error:
            session['missingStus'].append(f"{stu['profile']['name']['fullName']}'s email is not in OTData.")
            #stu['otdobject'] = None
        except Exception as error:
            session['missingStus'].append(f"{stu['profile']['name']['fullName']} had error: {error}")
            #stu['otdobject'] = None
        else:
            #stu['otdobject'] = otdstu
            # see if an enrollment exists, if it doesn't make one
            try:
                enrollment = GEnrollment.objects.get(owner=otdstu, gclassroom=currGClass)
            except:
                flash(f"NEW --> {index+1}/{numStus}: {stu['profile']['name']['fullName']}")
                enrollment=GEnrollment(
                    owner=otdstu,
                    gclassroom=currGClass
                    )
                enrollment.save()
            else:
                flash(f"Skipping --> {index+1}/{numStus}: {stu['profile']['name']['fullName']}")

        index = index + 1
        iterator = iterator + 1
        if iterator == numIterations:
            break
    
    if numStus > (index):
        # save the progress
        currGClass.update(grosterTemp=gstudents)
        # This is the url for the loading page to call back
        url = f"/getroster/{gclassid}/{index}"
        return render_template ('loading.html', url=url, nextIndex=index, total=numStus)

    currGClass.update(grosterTemp=gstudents)
    for stu in session['missingStus']:
        flash(stu)
    session.pop('missingStus',None)
    return redirect(url_for('roster',gclassid=gclassid))

@app.route('/genrollment/delete/<geid>/<gclassid>')
def genrollmentdelete(geid,gclassid):
    geDelete = GEnrollment.objects.get(pk=geid)
    geDelete.delete()
    return redirect(url_for('roster',gclassid=gclassid))


@app.route('/getguardians/<gclassid>/<index>')
@app.route('/getguardians/<gclassid>')
def getgaurdians(gclassid,index=0):
    if index == 0:
        session['tempGStudents'] = None

    index=int(index)

    # get the roster
    # iterate through each student and check if they have gaurdian 
    # if they don't have a gaurdian get the parent email and send invite
    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')    
    
    session['credentials'] = credentials_to_dict(credentials)
    classroom_service = googleapiclient.discovery.build('classroom', 'v1', credentials=credentials)

    try:
        session['tempGStudents']
    except:
        session['tempGStudents'] = []

    if not session['tempGStudents'] or len(session['tempGStudents'])==0:
        gstudents = []
        pageToken = None
        try:
            students_results = classroom_service.courses().students().list(courseId = gclassid,pageToken=pageToken).execute()
        except RefreshError:
            flash("When I asked for the courses from Google Classroom I found that your credentials needed to be refreshed.")
            return redirect('/authorize')

        while True:
            pageToken = students_results.get('nextPageToken')
            gstudents.extend(students_results['students'])
            if not pageToken:
                break
            students_results = classroom_service.courses().students().list(courseId = gclassid,pageToken=pageToken).execute()
        session['tempGStudents'] = gstudents

    # Remove students without s_ at the beginning of their address
    studentsOnly=[]
    for student in session['tempGStudents']:
        if student['profile']['emailAddress'][:2] == 's_':
            studentsOnly.append(student)

    session['tempGStudents'] = studentsOnly
    
    numStus = len(session['tempGStudents'])  
    numIterations = 3
    iterator = 0

    for student in session['tempGStudents'][index:]:
        # check for gaurdians
        guardians = classroom_service.userProfiles().guardians().list(studentId=student['userId']).execute()
        # see if the student is in OTData
        try:
            editStu = User.objects.get(otemail=student['profile']['emailAddress'])
        except:
            editStu = False
            flash(f"{student['profile']['emailAddress']} is not in OTData.")
        # if the student is in OTData AND has gaurdians, update the record
        if guardians and editStu:
                editStu.update(
                    gclassguardians = guardians
                )
        # Now check for invites      
        try:
            invites = classroom_service.userProfiles().guardianInvitations().list(studentId = student['userId']).execute()
        except:
            flash(f"Gaurdian invites failed for GID: {student['profile']['emailAddress']}.")

        if invites and editStu:
            editStu.update(
                gclassguardianinvites = invites
            )
        try: 
            numGuardians = len(guardians['guardians'])
        except:
            numGuardians = 0

        try:
            numInvites = len(invites['guardianInvitations'])
        except:
            numInvites = 0

        flash(f"{index+1}/{numStus}: {student['profile']['emailAddress']} Guardians: {numGuardians} Invites: {numInvites}")
        index = index + 1
        iterator = iterator + 1
        if iterator == numIterations:
            break

    if numStus > (index):
        # This is the url for the loading page to call back
        url = f"/getguardians/{gclassid}"

        return render_template ('loading.html', url=url, nextIndex=index, total=numStus)

    session['tempGStudents'] = None
    return redirect(url_for('roster',gclassid=gclassid))

@app.route('/inviteguardians/<gid>/<gclassid>/<gclassname>')
@app.route('/inviteguardians/<gid>')
def inviteguardians(gid,gclassid=None,gclassname=None):
    try:
        editStu = User.objects.get(gid=gid)
    except:
        editStu = False

    inviteEmails = []

    if editStu.adults:
        for adult in editStu.adults:
            inviteEmails.append(adult.email)
    elif editStu.aadultemail:
        inviteEmails.append(editStu.aadultemail)
    
    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')    
    
    session['credentials'] = credentials_to_dict(credentials)
    service = googleapiclient.discovery.build('classroom', 'v1', credentials=credentials)
    
    for inviteEmail in inviteEmails:
        guardianInvitation = {'invitedEmailAddress': inviteEmail}
        try:
            # TODO check the error msg to be sure it is cause it already exists
            guardianInvitation = service.userProfiles().guardianInvitations().create(
                                    studentId=editStu.otemail, 
                                    body=guardianInvitation
                                ).execute()
        except Exception as error:
            flash(f"Error: {error}")
            flash(f"Invite already exists for {inviteEmail}.")

    invites = service.userProfiles().guardianInvitations().list(studentId = gid).execute()
    if invites:
        editStu.update(
            gclassguardianinvites = invites
        )

    if gclassid and gclassname:
        return redirect(url_for('roster',gclassid=gclassid,gclassname=gclassname))
    else:
        return(redirect(url_for('profile',aeriesid=editStu.aeriesid)))

@app.route('/getcoursework/<gclassid>/<stage>/<index>')
@app.route('/getcoursework/<gclassid>/<stage>')
@app.route('/getcoursework/<gclassid>')
def getcw(gclassid,stage=0, index=0):
    stage=int(stage)
    index=int(index)
    if stage == 0:
        stage = 1
        flash("Retrieveing ALL assignments from Google Classroom.")
        url=f'/getcoursework/{gclassid}/{stage}'
        return render_template("loading.html",url=url)
    elif stage == 1:
        result = getCourseWork(gclassid)
        courseworkdict = result
        gClassroom = GoogleClassroom.objects.get(gclassid = gclassid)
        gClassroom.update(courseworkdict=courseworkdict)
        if result == "refresh":
            return redirect(url_for('authorize'))
        stage=2
        flash("Saving assignments to database.")
        url=f'/getcoursework/{gclassid}/{stage}'
        return render_template("loading.html",nextIndex=0,url=url)
    elif stage == 2:
        gClassroom = GoogleClassroom.objects.get(gclassid = gclassid)
        numAsses = len(gClassroom.courseworkdict['courseWork'])
        # How many loops to make before sending to loading page
        numIterations = 4
        for gAss in gClassroom.courseworkdict['courseWork'][index:index+numIterations]:
            index=index+1
            # TODO save assignment to gcoursework document
            try:
                gAss['topic']
            except:
                gAss['topic'] = None
            newCourseWork = CourseWork(
                courseworkdict = gAss,
                courseworkid = gAss['id'],
                gclassroom = gClassroom,
                topic = gAss['topic']
            )
            try:
                newCourseWork.save()
            except mongoengine.errors.NotUniqueError:
                flash(f"{gAss['title']} already exists. Updating.")
                editCourseWork = CourseWork.objects.get(courseworkid = gAss['id'])
                editCourseWork.update(
                    courseworkdict = gAss,
                    topic = gAss['topic']
                )
            if index == numAsses-1:
                flash("All assignments are saved.")
                return redirect(url_for('gClassAssignments',gclassid=gclassid))
        return render_template("loading.html", nextIndex=index, total = numAsses,url=f'/getcoursework/{gclassid}/{stage}/{index}')


@app.route('/listmissing/<gclassid>/<index>')
@app.route('/listmissing/<gclassid>')
def nummissing(gclassid,index=0):
    index=int(index)

    gclass = GoogleClassroom.objects.get(gclassid=gclassid)
    gclassname = gclass.gclassdict['name']

    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')    
    
    session['credentials'] = credentials_to_dict(credentials)
    classroom_service = googleapiclient.discovery.build('classroom', 'v1', credentials=credentials)

    if index == 0:
        session['startTimeTemp'] = dt.now()

    try:
        session['tempGStudents']
    except:
        session['tempGStudents'] = None
        session['startTimeTemp'] = dt.now()

    if not session['tempGStudents']:
        gstudents = []
        pageToken = None
        try:
            students_results = classroom_service.courses().students().list(courseId = gclassid,pageToken=pageToken).execute()
        except RefreshError:
            flash("When I asked for the courses from Google Classroom I found that your credentials needed to be refreshed.")
            return redirect('/authorize')

        while True:
            pageToken = students_results.get('nextPageToken')
            gstudents.extend(students_results['students'])
            if not pageToken:
                break
            students_results = classroom_service.courses().students().list(courseId = gclassid,pageToken=pageToken).execute()

        session['tempGStudents'] = gstudents

    # Remove students without s_ at the beginning of their address
    gStudentsOnly=[]
    for gStudent in session['tempGStudents']:
        if gStudent['profile']['emailAddress'][:2] == 's_':
            gStudentsOnly.append(gStudent)

    session['tempGStudents'] = gStudentsOnly
    
    numStus = len(session['tempGStudents'])  
    # How many loops to make before sending to loading page
    numIterations = 4

    for gstudent in session['tempGStudents'][index:index+numIterations]:
        index=index+1

        # See if student exists in OTData
        try:
            otdStudent = User.objects.get(gid = gstudent['userId'])
        except:
            flash(f"{gstudent['profile']['emailAddress']} is not in OTData.")
            otdStudent = None

            try:
                otdStudentClass = otdStudent.gclasses.get(gclassid = gclassid)
            except:
                otdStudentClass = None
                flash(f"Failed to find {gclassname} in {otdStudent.fname}'s OTData gclasses.")
            
            if otdStudent and otdStudentClass:
                flash(f"{otdStudent.fname} {otdStudent.alname}")
    
    if numStus > index:
        # elapsedTime = dt.now() - session['startTimeTemp']
        # # an approximation of how much time it took to process one student
        # currPerStuTime = elapsedTime / index
        # timeLeft = (numStus - (index+1)) * currPerStuTime
        return render_template ('loading.html', nextIndex=index, total=numStus)


    session['tempGStudents'] = None
    return redirect(url_for('roster',gclassid=gclassid))



@app.route('/assignments/list/<aeriesid>')
def missingassignmentslist(aeriesid):
    stu = User.objects.get(aeriesid=aeriesid)
    for gclass in stu.gclasses:
        if gclass.status and gclass.status.lower() == "active":
            result = getCourseWork(gclass.gclassid)
            if result == "refresh":
                return redirect(url_for('authorize'))
            elif result == False:
                return redirect(url_for('checkin'))

@app.route('/rostersort/<gclassid>/<sort>', methods=['GET', 'POST'])
@app.route('/rostersort/<gclassid>', methods=['GET', 'POST'])
def editrostersortorder(gclassid,sort=None):

    gclassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    enrollments = GEnrollment.objects(gclassroom=gclassroom)
    if sort:
        rosterToSort = enrollments
        rosterToSort = sorted(rosterToSort, key = lambda i: (i['sortCohort'], i['owner']['alname'], i['owner']['afname']))
        groster = rosterToSort
    else:
        groster = enrollments

    sortForms={}
    form=SortOrderCohortForm()

    if form.validate_on_submit():
        otStudent = User.objects.get(otemail = form.gmail.data)

        try:
            enrollment = GEnrollment.objects.get(owner=otStudent, gclassroom=gclassroom)
        except mongoengine.errors.DoesNotExist:
            flash(Markup(f"You need to <a href='/addgclass/{{otStudent.otemail}}/{{gclassid}}'>add {otStudent.fname} {otStudent.alname}</a> to the class."))
        else:
            enrollment.update(
                sortCohort = form.sortOrderCohort.data
            )
            enrollments = GEnrollment.objects(gclassroom=gclassroom)
            enrollments = sorted(enrollments, key = lambda i: (i['sortCohort'], i['owner']['alname'], i['owner']['afname']))

            groster = enrollments

    for i in range(len(groster)):

        try:
            sortOrderCohort = groster[i]['sortCohort']
        except KeyError:
            sortOrderCohort = None
        sortForms['form'+str(i)]=SortOrderCohortForm()
        sortForms['form'+str(i)].gid.data = groster[i]['owner']['id']
        sortForms['form'+str(i)].gmail.data = groster[i]['owner']['otemail']
        sortForms['form'+str(i)].gclassid.data = groster[i]['gclassroom']['id']
        sortForms['form'+str(i)].sortOrderCohort.data = sortOrderCohort
        if gclassroom.sortcohorts:
            choices = []
            for choice in gclassroom.sortcohorts:
                choices.append((choice,choice))
            sortForms['form'+str(i)].sortOrderCohort.choices = choices
        sortForms['form'+str(i)].order.data = i

    numForms = len(sortForms)

    return render_template('rostersortform.html.j2',gclassroom=gclassroom,forms=sortForms,numForms=numForms,groster=groster)

@app.route('/sortcohorts/<gcid>', methods=['GET','POST'])
def sortcohorts(gcid):

    googleClassroom = GoogleClassroom.objects.get(gclassid=gcid)

    form = SimpleForm()

    if form.validate_on_submit():
        cohorts = form.field.data
        sortCohorts = cohorts.split(',')
        googleClassroom.update(sortcohorts=sortCohorts)
        return redirect(url_for('editrostersortorder',gclassid=gcid))

    googleClassroom.reload()

    if googleClassroom.sortcohorts:
        form.field.data = ','.join(googleClassroom.sortcohorts)

    return render_template('sortcohorts.html',form=form,googleClassroom=googleClassroom)
    
