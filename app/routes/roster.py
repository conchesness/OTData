from re import S
from app import app
from .users import credentials_to_dict
from flask import render_template, redirect, session, flash, url_for
from app.classes.data import User, GoogleClassroom
from app.classes.forms import SimpleForm, SortOrderCohortForm
from datetime import datetime as dt
import mongoengine.errors
import google.oauth2.credentials
import googleapiclient.discovery
from google.auth.exceptions import RefreshError
import ast

@app.route("/roster/saved/<gclassid>", methods=['GET','POST'])
def rostersaved(gclassid):

    gclassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    gclassname = gclassroom.gclassdict['name']

    print(gclassroom.groster)

    return render_template('roster.html',gclassname=gclassname, gclassid=gclassid, otdstus=gclassroom.groster)

@app.route("/roster/<gclassid>/<gclassname>", methods=['GET','POST'])
@app.route("/roster/<gclassid>", methods=['GET','POST'])
def roster(gclassid,gclassname=None):
   
    # TODO create a function to retrieve roster cause I run this code three times
    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')    
    session['credentials'] = credentials_to_dict(credentials)
    classroom_service = googleapiclient.discovery.build('classroom', 'v1', credentials=credentials)
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

    otdstus=[]
    stus=[]
    for stu in gstudents:
        # Make sure the students are actually students
        if stu['profile']['emailAddress'][:2]=="s_":   
            stu['sortCohort'] = ''         
            try:
                # see if they are in OTData
                otdstu = User.objects.get(otemail=stu['profile']['emailAddress'])
                # If they are in OTData get any missing assignment data
            # TODO find the right error for does not exist
            except mongoengine.errors.DoesNotExist as error:
                flash(f"Possibly, {stu['profile']['emailAddress']} is not in OTData")
                flash(f"the exact error was: {error}")
                if error == "User matching query does not exist":
                    stu['numMissing'] = 0
                    stu['numMissingUpdate'] = None
            except Exception as error:
                flash(f'unknown error occured: {error}')
            try:
                otdStuClass = otdstu.gclasses.get(gclassid=gclassid)
            except mongoengine.errors.DoesNotExist as error:
                flash(f"A Mongoengine DoesNotExist error occured: {error}")
                stu['updateGClasses'] = "True"
                otdstus.append([stu,otdstu])
            except Exception as error:
                flash(f"An unknown error occured: {error}")
            else:
                stu['updateGClasses'] = "False"
                stu['missingLink'] = otdStuClass.missinglink

                try:
                    len(otdStuClass.missingasses['missing']) > 0
                except KeyError:
                    stu['numMissing'] = 0
                    stu['numMissingUpdate'] = None
                else:
                    if len(otdStuClass.missingasses['missing']) > 0:
                        stu['numMissing'] = otdStuClass.nummissing
                        stu['numMissingUpdate'] = otdStuClass.nummissingupdate.date().strftime("%m/%d/%Y")
                try:
                    if otdStuClass.sortcohort:
                        stu['sortCohort'] = otdStuClass.sortcohort
                except KeyError:
                    pass
                otdstus.append([stu,otdstu])
        stus.append(stu)

    otdstus = sorted(otdstus, key = lambda i: (i[0]['sortCohort'],i[0]['profile']['name']['familyName']))

    groster = {}
    groster['roster'] = stus

    googleClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    # print(googleClassroom.gclassdict)
    if not gclassname:
        gclassname = googleClassroom.gclassdict['name']

    googleClassroom.update(
            groster = groster
        )

    return render_template('roster.html',gclassname=gclassname, gclassid=gclassid, otdstus=otdstus)

@app.route('/getguardians/<gclassid>/<gclassname>/<index>')
@app.route('/getguardians/<gclassid>/<gclassname>')
def getgaurdians(gclassid,gclassname,index=0):
    if index == 0:
        session['tempGStudents'] = None

    # startIterationTime = dt.now()
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
        #students_results = classroom_service.courses().students().list(courseId = gclassid,pageToken=pageToken).execute()
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
    numIterations = 2
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
        url = f"/getguardians/{gclassid}/{gclassname}"

        return render_template ('loading.html', url=url, nextIndex=index, total=numStus)

    session['tempGStudents'] = None
    return redirect(url_for('roster',gclassid=gclassid,gclassname=gclassname))

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

def getCourseWork(gclassid):
    pageToken = None
    assignmentsAll = {}
    assignmentsAll['courseWork'] = []

    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')    
    
    session['credentials'] = credentials_to_dict(credentials)
    classroom_service = googleapiclient.discovery.build('classroom', 'v1', credentials=credentials)

    # TODO get all assignments and add as dict to gclassroom record
    while True:
        try:
            assignments = classroom_service.courses().courseWork().list(
                    courseId=gclassid,
                    pageToken=pageToken,
                    ).execute()
        except RefreshError:
            return redirect(url_for('authorize'))

        except Exception as error:
            # print(type(error))    # the exception instance
            # print(error.args)     # arguments stored in .args
            # print(error)          # __str__ allows args to be printed directly,
            #                      # but may be overridden in exception subclasses
            x, y = error.args     # unpack args
            # print(f"x type: {type(x)}")
            # print(f"y type: {type(y)}")
            #print('x =', x)
            #print('y =', y)
            if isinstance(y, bytes):
                y = y.decode("UTF-8")
            errorDict = ast.literal_eval(y)
            if errorDict['error'] == 'invalid_grant':
                print(f"Got Error: {errorDict}")
                flash('Your login has expired. You need to re-login.')
                return "AUTHORIZE"
            elif errorDict['error']['status'] == "PERMISSION_DENIED":
                print(f"Got Error: {errorDict}")
                return "PERMISSION_DENIED"
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
    gclassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    gclassroom.update(courseworkdict = assignmentsAll)
    return True

def getmissing(gid, aeriesid, gclassid):
    missStudSubsAll = []
    pageToken=None 

    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')    
    
    session['credentials'] = credentials_to_dict(credentials)
    classroom_service = googleapiclient.discovery.build('classroom', 'v1', credentials=credentials)

    while True:
        try:
            missStudSubs = classroom_service.courses().courseWork().studentSubmissions().list(
                userId = gid,
                courseId=gclassid,
                courseWorkId='-',
                late = "LATE_ONLY",
                pageToken=pageToken
            ).execute()
        except RefreshError:
            return "AUTHORIZE"

        except Exception as error:
            # print(type(error))    # the exception instance
            # print(error.args)     # arguments stored in .args
            # print(error)          # __str__ allows args to be printed directly,
            #                      # but may be overridden in exception subclasses
            x, y = error.args     # unpack args
            # print(f"x type: {type(x)}")
            # print(f"y type: {type(y)}")
            #print('x =', x)
            #print('y =', y)
            if isinstance(y, bytes):
                y = y.decode("UTF-8")
            errorDict = ast.literal_eval(y)
            if errorDict['error'] == 'invalid_grant':
                print(f"Got Error: {errorDict}")
                flash('Your login has expired. You need to re-login.')
                return "LOGIN"
            elif errorDict['error']['status'] == "PERMISSION_DENIED":
                print(f"Got Error: {errorDict}")
                flash(f"You do not have permission to access this class for this student.")
                return "PERMISSION_DENIED"
            else:
                flash(f"Got unknown Error: {errorDict}")
                return "UNKNOWN"
        else:
            countMissing = 0
            try:
                subs = missStudSubs['studentSubmissions']
            except:
                pass
            else:
                for item in subs:

                    try:
                        assignedGrade = int(item['assignedGrade']) > 0
                    except:
                        assignedGrade = False

                    # for subHistoryItem in item['submissionHistory']:
                    #     try:
                    #         gradeHistory = subHistoryItem['gradeHistory']
                    #     except:
                    #         gradeHistory = None

                    if (assignedGrade == False and item['state'] != "TURNED_IN"):
                        missing = True
                        countMissing += 1
                        #print(f"Missing: {missing} id: {item['id']} Late: {late} State: {item['state']} courseWorkType: {item['courseWorkType']} AssignedGrade: {assignedGrade} GradeHistory: {gradeHistory}")
        try: 
            missStudSubsAll.extend(missStudSubs['studentSubmissions'])
        # UnboundLocalError happens when missStudSubs does not exist
        # KeyError happens when missStudSubs dict exists BUT the studentSubmissions key does not
        # in both cases there will be no nextPageToken
        except (KeyError, UnboundLocalError):
            pass
        else:
            pageToken = missStudSubs.get('nextPageToken')

        if not pageToken:
            break

    missingAsses = {}
    missingAsses['missing'] = missStudSubsAll
    print(len(missingAsses['missing']))
    return missingAsses

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
            missingAsses = None
        else:
            # Run getmissing function
            missingAsses = getmissing(gstudent['userId'],otdStudent.aeriesid,gclassid)

        if missingAsses == "AUTHORIZE":
            flash("Need to re-authorize with Google to get these assignments.")
            return redirect(url_for('authorize'))
        elif missingAsses == "LOGIN":
            flash("Your login has expired.")
            return redirect(url_for('login'))

        # the getmissing function should return 'False' if an error occurs and 0 if no error but none are found.
        if missingAsses:
            numMissStudSubs = len(missingAsses['missing'])
        else:
            continue

        # save numMissStudSubs to the students GClasses embedded doc list field
        # in the nummissing field and the date in the nummissingupdate field

        # TODO add MissingLink like in Roster
        if otdStudent and missingAsses:

            try:
                otdStuClass = otdStudent.gclasses.get(gclassid = gclassid)
            except mongoengine.errors.DoesNotExist:
                flash(f"could not find class in OTData")
                otdStuClass = None
            if otdStuClass:
                try:
                    otdStuClass.missingasses['missing']
                except KeyError:
                    missinglink = None
                else:
                    try:
                        end = otdStuClass.missingasses['missing'][0]['alternateLink']
                    except:
                        missinglink = None
                    else:
                        beginning = otdStuClass.gclassroom.gclassdict['alternateLink']
                        print(end)
                        inverseEnd = end[::-1]
                        indexFromEnd = inverseEnd.index('/')
                        end = end[indexFromEnd*-1:]
                        missinglink = f"{beginning}/sp/{end}/m"

                otdStudent.gclasses.filter(gclassid = gclassid).update(
                    nummissing = str(numMissStudSubs),
                    nummissingupdate = dt.utcnow(),
                    missingasses = missingAsses,
                    missinglink = missinglink
                )
                otdStudent.save()

            try:
                otdStudentClass = otdStudent.gclasses.get(gclassid = gclassid)
            except:
                otdStudentClass = None
                flash(f"Failed to find {gclassname} in {otdStudent.fname}'s OTData gclasses.")
            
            if otdStudent and otdStudentClass:
                flash(f"{otdStudent.fname} {otdStudent.alname} Missing: {otdStudentClass.nummissing}")

    url = f"/listmissing/{gclassid}"
    
    if numStus > index:
        # elapsedTime = dt.now() - session['startTimeTemp']
        # # an approximation of how much time it took to process one student
        # currPerStuTime = elapsedTime / index
        # timeLeft = (numStus - (index+1)) * currPerStuTime
        return render_template ('loading.html', url=url, nextIndex=index, total=numStus)


    session['tempGStudents'] = None
    return redirect(url_for('roster',gclassid=gclassid))

@app.route('/missingassignmentsstu/<gid>')
def missingassignmentsstu(gid):
    student = User.objects.get(gid=gid)
    for gclass in student.gclasses:
        if gclass.status and gclass.status.lower() == 'active':
            missingAsses = getmissing(student.gid,student.aeriesid,gclass.gclassid)
            if missingAsses == "AUTHORIZE":
                flash("Need to re-authorize with Google to get these assignments.")
                return redirect(url_for('authorize'))
            elif missingAsses == "LOGIN":
                flash("Your login has expired.")
                return redirect(url_for('login'))
            elif len(missingAsses['missing']) >= 0:
                numMissing = len(missingAsses['missing'])
            else:
                continue

            otdStuClass = gclass
            try: 
                otdStuClass.missingasses['missing']
            except:
                missinglink = None
            else:
                if len(otdStuClass.missingasses['missing']) > 0:
                    beginning = otdStuClass.gclassroom.gclassdict['alternateLink']
                    end = otdStuClass.missingasses['missing'][0]['alternateLink']
                    print(end)
                    inverseEnd = end[::-1]
                    indexFromEnd = inverseEnd.index('/')
                    end = end[indexFromEnd*-1:]
                    missinglink = f"{beginning}/sp/{end}/m"

            student.gclasses.filter(gclassid = gclass.gclassid).update(
                nummissing = str(numMissing),
                nummissingupdate = dt.utcnow(),
                missingasses = missingAsses,
                missinglink = missinglink
            )
            student.save()

    return redirect(url_for('profile',aeriesid=student.aeriesid))

@app.route('/assignments/list/<aeriesid>')
def missingassignmentslist(aeriesid):
    stu = User.objects.get(aeriesid=aeriesid)
    for gclass in stu.gclasses:
        # if gclass.missingasses:
        #     for missingAss in gclass.missingasses:
        #         if missingAss in 
        # update the assignment list if there is none
        if gclass.status and gclass.status.lower() == "active":
            getCourseWorkResult = getCourseWork(gclass.gclassid)
            print(f"Result: {getCourseWorkResult}")
            if getCourseWorkResult == "AUTHORIZE":
                return redirect(url_for('authorize'))
            elif getCourseWorkResult == "PERMISSION_DENIED":
                flash(f"You do not have permission to access {gclass.gclassroom.gclassdict['name']} for this student.")
            elif not getCourseWorkResult:
                flash(f"An error occured. I was unable to update the assignment list for {gclass.gclassroom.gclassdict['name']}.")
            elif getCourseWorkResult:
                flash(f"Saved assignment list for {gclass.gclassroom.gclassdict['name']}")

    # # TODO iterate through each missing assingment which are saved at gclass.missingasses. If it doesn't exist update the list


    return render_template('missasslist.html.j2',stu=stu)

@app.route('/rostersort/<gclassid>/<sort>', methods=['GET', 'POST'])
@app.route('/rostersort/<gclassid>', methods=['GET', 'POST'])
def editrostersortorder(gclassid,sort=None):

    gclassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    if sort:
        rosterToSort = gclassroom.groster['roster']
        rosterToSort = sorted(rosterToSort, key = lambda i: (i['sortCohort'], i['profile']['name']['familyName']))
        groster = {}
        groster['roster'] = rosterToSort
        gclassroom.update(
            groster=groster
        )
    else:
        groster = gclassroom.groster

    sortForms={}
    form=SortOrderCohortForm()

    if form.validate_on_submit():
        #otStudent = User.objects.get(gid = form.gid.data)
        otStudent = User.objects.get(otemail = form.gmail.data)

        try:
            otStudent.gclasses.get(gclassid = form.gclassid.data)
        except mongoengine.errors.DoesNotExist:
            flash(f"{otStudent.fname} {otStudent.alname} does not have this class in their classes list.")
        else:
            otStudent.gclasses.filter(gclassid = form.gclassid.data).update(
                sortcohort = form.sortOrderCohort.data
            )
            otStudent.save()

            gclassroom.groster['roster'][int(form.order.data)]['sortCohort'] = form.sortOrderCohort.data
            gclassroom.update(
                groster = gclassroom.groster
            )
            #groster = gclassroom.groster
            rosterToSort = gclassroom.groster['roster']
            rosterToSort = sorted(rosterToSort, key = lambda i: (i['sortCohort'], i['profile']['name']['familyName']))
            groster = {}
            groster['roster'] = rosterToSort
            gclassroom.update(
                groster=groster
            )



    for i in range(len(groster['roster'])):

        try:
            sortOrderCohort = groster['roster'][i]['sortCohort']
        except KeyError:
            sortOrderCohort = None

        sortForms['form'+str(i)]=SortOrderCohortForm()
        sortForms['form'+str(i)].gid.data = groster['roster'][i]['userId']
        sortForms['form'+str(i)].gmail.data = groster['roster'][i]['profile']['emailAddress']
        sortForms['form'+str(i)].gclassid.data = groster['roster'][i]['courseId']
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
        print(googleClassroom.sortcohorts)
        print(form.field.data)

    return render_template('sortcohorts.html',form=form,googleClassroom=googleClassroom)
    
