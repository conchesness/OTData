from app.routes.coursecat import course
from app import app
from .scopes import SCOPESOT, SCOPESCOMMUNITY
from flask import render_template, redirect, url_for, request, session, flash, Markup
from app.classes.data import User, CheckIn, Post, Group, Section
from app.classes.forms import UserForm, AdultForm, CohortForm, PostGradForm
from .credentials import GOOGLE_CLIENT_CONFIG
from mongoengine import Q
from mongoengine.connection import get_db
from bson.objectid import ObjectId
import requests
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import datetime as dt
import re

# List of email addresses for Admin users
admins = ['stephen.wright@ousd.org','sara.ketcham@ousd.org','jelani.noble@ousd.org']
courseCatAdmins = []

# Do not edit anything in this function.  This is just for google authentication
def credentials_to_dict(credentials):
    return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes
          }

# Function to format phone numbers before sending to template
def formatphone(phnum):
    phnum = str(phnum)
    phnum = f"({phnum[0:3]}) {phnum[3:6]}-{phnum[6:]}"
    return phnum

# Function to record edits to user and related adult records
def userModified(editUser):
    currUser = User.objects.get(pk = session['currUserId'])
    editUser.lastedited.append([dt.datetime.utcnow(),currUser]) 
    if len(editUser.lastedited) > 20:
        editUser.lastedited.pop(0)
    print(editUser.casemanager)
    editUser.save()

# Function to strip non-numbers from mobile text 
def phstr2int(phstr):
    phnum = re.sub("[^0-9]", "", phstr)
    if len(phnum) == 0:
        phnum = 0
    phnum = int(phnum)
    if phnum > 1000000000 and phnum < 9999999999: 
        phvalid = True
    else:
        phvalid = False

    return (phvalid, phnum)

# This runs before every route and serves to make sure users are using a secure site and can only
# access pages they are allowed to access
@app.before_request
def before_request():
    try:
        if session['isadmin']:
            db = get_db()
            session['db'] = db.name
            flash(session['db'])
    except:
        pass

    # this checks if the user requests http and if they did it changes it to https
    if not request.is_secure:
        url = request.url.replace("http://", "https://", 1)
        code = 301
        return redirect(url, code=code)

    # Create a list of all the paths that do not need authorization or are part of authorizing
    # so that each path this is *not* in this list requires an authorization check.
    # If you have urls that you want your user to be able to see without logging in add them here.
    # TODO create a decorator or something for this
    unauthPaths = ['/','/home','/authorize','/login','/oauth2callback','/static','/logout','/revoke','/msgreply','/msgstatus']   
    communityPaths = ['/profile','/editprofile','/findstufromadult','/addstutoadult']
    studentPaths = ['/postgrad','/cc','/plan','/profile','/editprofile','/addadult','/editadult','/deleteadult','/sendstudentemail','/checkin','/deletecheckin','/editgclass','/gclasses','/comp','/missingassignmentsstu'] 
    # this is some tricky code designed to send the user to the page they requested even if they have to first go through
    # a authorization process.
    try: 
        session['return_URL']
    except:
        session['return_URL'] = '/'

    # find the first path argument in the URL
    basePath = request.path
    basePath = basePath.split('/')
    basePath = '/'+basePath[1]

    # this sends users back to authorization if the login has timed out or other similar stuff
    if basePath not in unauthPaths:
        session['return_URL'] = request.path
        if 'credentials' not in session:
            flash(f'Adding credentials to session')
            return redirect(url_for('authorize'))
        if not google.oauth2.credentials.Credentials(**session['credentials']).valid:
            flash('session credentials not valid')
            return redirect(url_for('authorize'))
        else:
            # refresh the session credentials
            if google.oauth2.credentials.Credentials(**session['credentials']).valid:
                credentials = google.oauth2.credentials.Credentials(**session['credentials'])
            else:
                return redirect('/authorize')

            session['credentials'] = credentials_to_dict(credentials)
            # reset the return_URL
            session['return_URL'] = request.full_path
            if session['role'].lower() == 'student':
                for studentPath in studentPaths:
                    match = re.match(f"{studentPath}.*", basePath)
                    if match:
                        return
            if session['role'].lower() in ['community','parent']:
                for communityPath in communityPaths:
                    match = re.match(f"{communityPath}.*", basePath)
                    if match:
                        return
            if session['role'].lower() == 'student':
                # Send students to their profile page
                flash(f"Unfortunately, you do not have access to the url '{basePath}'.")
                return redirect(url_for('profile'))

# This tells the app what to do if the user requests the home either via '/home' or just'/'
@app.route('/home')
@app.route('/')
def index():

    #Get any announcements
    try:
        announcement = Post.objects.first()
        announceBody = Markup(announcement.body)
    except:
        announcement = None
        announceBody = None

    #get the curent requesting this page but include error handling because the user might not be logged in
    try: 
        currUser = User.objects.get(pk=session['currUserId'])
        # If this is a student, send them to their profile page
        if session['role'].lower() == 'student':
            return redirect(url_for('profile',aeriesid=currUser.aeriesid))
    except:
        currUser=None

    return render_template("index.html", announceBody=announceBody, announcement=announcement, currUser=currUser)


# a lot of stuff going on here for the user as they log in including creatin new users if this is their first login
@app.route('/login/<audience>')
@app.route('/login')
def login(audience=None):

    # Set audience in the session so the user can be asked for the appropriate privledges from google
    if audience == "ot":
        session['audience'] = "ot"
    elif audience == "community":
        session['audience'] = "community"
    else:
        try:
            audience = session['audience']
        except:
            session['audience'] = None

    if session['audience'] == None:
        flash(Markup(f'You must designate your community.<br>login as Oakland Tech <br> <a href="/login/ot">Student/Staff</a>  <br>or <br> <a href="/login/community">Parent, Alumni, Community</a>' ))
        return redirect("/")

    # Go and get the users credentials from google. The /authorize and /oauth2callback functions should not be edited.
    # That is where the user is sent if their credentials are not currently stored in the session.  More about sessions below. 
    if 'credentials' not in session:
        # send the user to get authenticated by google
        return redirect(url_for('authorize'))

    # Now that the user has credentials, use those credentials to access Google's people api and get the users information
    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')    
    session['credentials'] = credentials_to_dict(credentials)
    people_service = googleapiclient.discovery.build('people', 'v1', credentials=credentials)

    # set data to be the dictionary that contains all the information about the user that google has.  You can see this 
    # information displayed via the current profile template
    data = people_service.people().get(resourceName='people/me', personFields='names,emailAddresses,photos').execute()

    #TODO there is def a more efficient way to do this!
    if data['emailAddresses'][0]['value'][-8:] == "ousd.org":
        if session['audience'].lower() == 'community':
            session['audience'] = "ot"
            if data['emailAddresses'][0]['value'][0:2] == "s_":
                session['role'] = 'Student'
                flash(f'You have an ousd.org email address but you are logging in as a community member. Switching you to OT and Student role.')
            else:
                session['role'] = 'Teacher'
                flash(f'You have an ousd.org email address but you are logging in as a community member. Switching you to OT and Teacher role.')
        elif session['audience'].lower() == 'ot' and data['emailAddresses'][0]['value'][0:2] == "s_":
            session['role'] = 'Student'
            session['audience'] = "ot"
        elif session['audience'].lower() == 'ot':
            session['role'] = 'Teacher'
            session['audience'] = "ot"
    else:
        session['audience'] = "community"
        session['role'] = 'Community'

    if data['emailAddresses'][0]['value'] in admins:
        session['isadmin'] = True
    else:
        session['isadmin'] = False

    if data['emailAddresses'][0]['value'] in courseCatAdmins:
        session['courseCatAdmin'] = True
    else:
        session['courseCatAdmin'] = False

    if session['audience'].lower() == "ot":
        try:
            currUser = User.objects.get(otemail = data['emailAddresses'][0]['value'])
        except:
            flash('You are not in the database.  Please contact Steve Wright (stephen.wright@ousd.org) to get access or login as community. ')
            return redirect('/')
    elif session['audience'].lower() == "community":
        session['role'] = 'Community'
        try:
            currUser = User.objects.get(otemail = data['emailAddresses'][0]['value'])
        except:
            currUser = User(
                otemail=data['emailAddresses'][0]['value'],
                gid=data['emailAddresses'][0]['metadata']['source']['id'],
                role=session['role'],
                afname=data['names'][0]['givenName'],
                alname=data['names'][0]['familyName'],
                fname=data['names'][0]['givenName'],
                lname=data['names'][0]['familyName']
            )
            currUser.save()

    if not currUser.gid:
        currUser.update(
            gid=data['emailAddresses'][0]['metadata']['source']['id'],
            role=session['role'],
            isadmin=session['isadmin']
        )
        currUser.reload()

    if not currUser.role == session['role']:
        currUser.update(
            role = session['role']
        )
        currUser.reload()
    
    if currUser.isadmin != session['isadmin']:
        currUser.update(
            isadmin=session['isadmin'] 
        )
        currUser.reload()

    # update lastlogin
    currUser.update(
        lastlogin = dt.datetime.utcnow()
    )

    if currUser.ufname:
        fname = currUser.ufname
    else:
        fname = currUser.afname

    if currUser.ulname:
        lname = currUser.ulname
    else:
        lname = currUser.alname

    if fname != currUser.fname or lname != currUser.lname:
        currUser.update(
            fname = fname,
            lname = lname
        )
    
    # Set the session variables
    session['displayName'] = f"{currUser.fname} {currUser.lname}"
    session['currUserId'] = str(currUser.id)
    session['aeriesid'] = currUser.aeriesid
    session['gid'] = currUser.gid
    session['fname'] = currUser.fname
    session['lname'] = currUser.lname

    # this stores the entire Google Data object in the session
    session['gdata'] = data
    session['role'] = currUser.role
    session['isadmin'] = currUser.isadmin
    session['email'] = data['emailAddresses'][0]['value']

    flash(f"Hello {session['fname']} {session['lname']}.")

    # The return_URL value is set above in the before_request route. This redirects a user to login and then
    # sent to the page they originally asked for.
    return redirect(session['return_URL'])

#get the profile page for a designated or the logged in user. Can use either gid or aeriesid.
#TODO change this to GID instead of AeriesId so Teacher profiles can be accessed
@app.route('/profile/<aeriesid>', methods=['GET', 'POST'])
@app.route('/profile', methods=['GET', 'POST'])
def profile(aeriesid=None):

    if aeriesid == 'None':
        aeriesid = None 

    if session['role'].lower() != "teacher":
        targetUser = User.objects.get(id = session['currUserId'])
        groups=None
        if aeriesid and aeriesid != targetUser.gid:
            flash('You can only view your own profile.')
            return redirect(url_for('profile'))

    elif aeriesid and len(aeriesid) < 7:
        try:
            targetUser = User.objects.get(aeriesid=aeriesid)
        except:
            flash(f"Aeries ID {aeriesid} is not in the database, displaying your profile instead. Contact Steve Wright if you feel this is an error (stephen.wright@ousd.org).")
            targetUser=User.objects.get(gid=session['gid'])

    elif aeriesid and len(aeriesid) > 6:
        try:
            targetUser = User.objects.get(gid=aeriesid)
        except:
            flash(f"The Google ID {aeriesid} is not in the database, displaying your profile instead. Contact Steve Wright if you feel this is an error (stephen.wright@ousd.org).")
            targetUser=User.objects.get(gid=session['gid'])
    else:
        try:
            targetUser=User.objects.get(gid=session['gid'])
        except:
            flash("You are not in the database of users which doesn't make sense cause you're already looged in. Sorry this shouldn't ever happen. (stephen.wright@ousd.org).")
            return redirect('/')

    if targetUser.role.lower() == "student":
        checkins = CheckIn.objects(student=targetUser).limit(15)
    else:
        checkins = None

    form = CohortForm()

    cohorts = User.objects().distinct(field="cohort")
    cohortslist = [("","None")]
    for cohort in cohorts:
        if len(cohort) > 0:
            cohortslist.append((cohort,cohort))

    form.cohort.choices = cohortslist

    casemanagers = User.objects().distinct(field="casemanager")
    casemanagerslist = [("","---")]
    for casemanager in casemanagers:
        if len(cohort) > 0:
            casemanagerslist.append((casemanager,casemanager))
            
    form.casemanager.choices = casemanagerslist
    
    if form.validate_on_submit():
        if len(form.casemanager.data) > 0:
            targetUser.update(
                cohort = form.cohort.data,
                casemanager = form.casemanager.data
            )
        else:
            targetUser.update(
                cohort = form.cohort.data,
                unset__casemanager = 1
            )
        targetUser.reload()

    form.cohort.data = targetUser.cohort
    form.casemanager.data = targetUser.casemanager
    dttoday = dt.datetime.utcnow()

    if session['role'].lower()!='student':
        currUser=User.objects.get(pk=session['currUserId'])
        groups = Group.objects(owner=currUser)
    else:
        groups=None

    if targetUser.role.lower() == "teacher":
        sections = Section.objects(teacher = targetUser)
    else:
        sections = None

    return render_template("profile/profile.html",groups=groups,currUser=targetUser, data=session['gdata'], form=form, today=dttoday, checkins=checkins, sections=sections)

# to get an in depth description of how creating, editing and deleting database recodes work check
# out the feedback.py file.
# This route anables the current user to edit some values in their profile.
@app.route('/editprofile', methods=['GET', 'POST'])
@app.route('/editprofile/<aeriesid>', methods=['GET', 'POST'])
def editprofile(aeriesid=None):

    # create a form object from the UserForm Class
    form = UserForm()
    # get the user object that is going to be edited which will be the current user so we user the 
    # googleId from the active session to load the right record

    if session['role'].lower() != 'student' and aeriesid:
        print('bob')
        editUser = User.objects.get(aeriesid=aeriesid)
    else:
        editUser = User.objects.get(gid=session['gid'])

    # first see if the form was posted and then reformat the phone numbers
    if request.method == 'POST':
        phvalid = []

        if form.mobile.data:
            response = phstr2int(form.mobile.data)
            if response[0]:
                form.mobile.data = response[1]
                phvalid.append(True)
            else:
                flash(f"Mobile phone number {form.mobile.data} is not a phone number.")
                phvalid.append(False)
        else:
            form.mobile.data = None

        if form.altphone.data:
            response = phstr2int(form.altphone.data)
            if response[0]:
                form.altphone.data = response[1]
                phvalid.append(True)
            else:
                flash(f"Other phone number {form.altphone.data} is not a phone number.")
                phvalid.append(False)
        else:
            form.altphone.data = None

    if form.validate_on_submit() and not False in phvalid:

        editUser.update(
            ufname = form.fname.data,
            ulname = form.lname.data,
            pronouns = form.pronouns.data,
            ustreet = form.ustreet.data,
            ucity = form.ucity.data,
            ustate = form.ustate.data,
            uzipcode = form.uzipcode.data,
            mobile = form.mobile.data,
            altphone = form.altphone.data,
            personalemail = form.personalemail.data,
            ugender = form.ugender.data,
            uethnicity = form.uethnicity.data,
            uethnicityother = form.uethnicityother.data,
            linkedin = form.linkedin.data,
            shirtsize = form.shirtsize.data
        )
        # Record edit datetime to user record
        userModified(editUser)

        if form.image.data:
            editUser.image.delete()
            editUser.image.put(form.image.data, content_type = 'image/jpeg')
            editUser.save()

        if editUser.ufname:
            fname = editUser.ufname
        else:
            fname = editUser.afname

        if editUser.ulname:
            lname = editUser.ulname
        else:
            lname = editUser.alname

        if fname != editUser.fname or lname != editUser.lname:
            editUser.update(
                fname = fname,
                lname = lname
            )

        # after the profile is updated, send the user to the profile page
        return redirect(url_for('profile', aeriesid=aeriesid))

    #if their is an expressed preferred value prefill the form with that otherwise use the one from aeries
    if editUser.ufname:
        form.fname.data = editUser.ufname
    else:
        form.fname.data = editUser.afname

    if editUser.ufname:
        form.lname.data = editUser.ulname
    else:
        form.lname.data = editUser.alname

    if editUser.ustreet:
        form.ustreet.data = editUser.ustreet
    else:
        form.ustreet.data = editUser.astreet

    if editUser.ustate:
        form.ustate.data = editUser.ustate
    else:
        form.ustate.data = editUser.astate

    if editUser.uzipcode:
        form.uzipcode.data = editUser.uzipcode
    else:
        form.uzipcode.data = editUser.azipcode

    if editUser.ucity:
        form.ucity.data = editUser.ucity
    else:
        form.ucity.data = editUser.acity

    form.pronouns.data = editUser.pronouns
    form.image.data = editUser.image
    form.personalemail.data = editUser.personalemail
    form.mobile.data = editUser.mobile
    form.altphone.data = editUser.altphone
    form.uethnicity.data = editUser.uethnicity
    form.uethnicityother.data = editUser.uethnicityother
    form.ugender.data = editUser.ugender
    form.linkedin.data = editUser.linkedin
    form.shirtsize.data = editUser.shirtsize

    # render the editprofile template and send the pre-populated form object.
    return render_template('profile/editprofile.html', form=form, editUser=editUser)

@app.route('/findemail/<email>')
def findemail(email):
    query = (Q(personalemail = email) | Q(adults__email = email) | Q(adults__altemail=email))
    user = User.objects.get(query)
    flash(f"{user.fname} {user.lname}")
    return redirect(url_for('profile', aeriesid = user.aeriesid))

@app.route('/findphnum/<phnum>')
def findphnum(phnum):
    query = (Q(aadult1phone = phnum) | Q(aadult2phone = phnum) | Q(aphone=phnum) | Q(mobile=phnum) | Q(altphone=phnum) | Q(adults__mobile = phnum) | Q(adults__altphone = phnum))
    user = User.objects.get(query)
    flash(f"{user.fname} {user.lname}")
    return redirect(url_for('profile', aeriesid = user.aeriesid))   

@app.route('/findstufromadult')
def findstufromadult():
    communityUser = User.objects.get(gid=session['gid'])
    students = User.objects(role__iexact = 'student')
    for student in students:
        if student.aadultemail == communityUser.otemail:
            flash(Markup(f'Student {student.fname} {student.lname} has an adult listed in Aeries with your email. <a href="/addstutoadult/{student.id}">This is my student.</a>'))
        for adult in student.adults:
            if communityUser.otemail == adult.email or communityUser.otemail == adult.altemail:
                flash(Markup(f'Student {student.fname} {student.lname} has added an adult listed with your email. <a href="/addstutoadult/{student.id}">This is my student.</a>'))
    return redirect("/profile")

@app.route('/addstutoadult/<stuid>')
def addstutoadult(stuid):
    communityUser = User.objects.get(gid=session['gid'])
    student = User.objects.get(pk=stuid)


    # Associate the student to the parent
    communityUser.this_parents_students.append(student)
    communityUser.this_parents_students = list(set(communityUser.this_parents_students))
    communityUser.save()

    # Associate the parent to the student
    student.this_students_parents.append(communityUser)
    student.this_students_parents = list(set(student.this_students_parents))
    student.save()

    # set the communityUser as a parent
    communityUser.update(
        role = "parent"
        )

    flash(f"Student {student.fname} {student.lname} was added to Community User {communityUser.fname} {communityUser.lname} and vice versa.")
    return redirect("/profile")

@app.route('/addadult/<aeriesid>', methods=['GET', 'POST'])
def addadult(aeriesid):
    editUser = User.objects.get(aeriesid = aeriesid)
    form = AdultForm()

    if request.method == 'POST':
        phvalid = []

        if form.mobile.data:
            response = phstr2int(form.mobile.data)
            if response[0]:
                form.mobile.data = response[1]
                phvalid.append(True)
            else:
                flash(f"Mobile phone number {form.mobile.data} is not a phone number.")
                phvalid.append(False)
        else:
            form.mobile.data = None

        if form.altphone.data:
            response = phstr2int(form.altphone.data)
            if response[0]:
                form.altphone.data = response[1]
                phvalid.append(True)
            else:
                flash(f"Other phone number {form.altphone.data} is not a phone number.")
                phvalid.append(False)
        else:
            form.altphone.data = None
    
    if form.validate_on_submit() and not False in phvalid:
        editUser.adults.create(
                oid = ObjectId(),
                preferredcontact = form.preferredcontact.data,
                relation = form.relation.data,
                fname = form.fname.data,
                lname = form.lname.data,
                mobile = form.mobile.data,
                altphone = form.altphone.data,
                email = form.email.data,
                altemail = form.altemail.data,
                street = form.street.data,
                city = form.city.data,
                state = form.state.data,
                zipcode = form.zipcode.data,
                notes = form.notes.data,
                primarylang = form.primarylang.data,
                needstranslation = form.needstranslation.data
            )
        editUser.save()
        # Record edit datetime to user record
        userModified(editUser)
        return redirect(url_for('profile', aeriesid=aeriesid))

    return render_template('editadult.html',form=form,editUser=editUser)

@app.route('/editadult/<aeriesid>/<adultoid>', methods=['GET', 'POST'])
def editadult(aeriesid,adultoid):
    editUser = User.objects.get(aeriesid=aeriesid)
    editAdult = editUser.adults.get(oid=adultoid)

    form = AdultForm()

    # first see if the form was posted and then reformat the phone numbers
    if request.method == 'POST':
        phvalid = []

        if form.mobile.data:
            response = phstr2int(form.mobile.data)
            if response[0]:
                form.mobile.data = response[1]
                phvalid.append(True)
            else:
                flash(f"Mobile phone number {form.mobile.data} is not a phone number.")
                phvalid.append(False)
        else:
            form.mobile.data = None

        if form.altphone.data:
            response = phstr2int(form.altphone.data)
            if response[0]:
                form.altphone.data = response[1]
                phvalid.append(True)
            else:
                flash(f"Other phone number {form.altphone.data} is not a phone number.")
                phvalid.append(False)
        else:
            form.altphone.data = None

    if form.validate_on_submit() and not False in phvalid:

        # different syntax for updating an Embedded Document. replace the fields then save to parent doc.
        editUser.adults.filter(oid=adultoid).update(
            preferredcontact = form.preferredcontact.data,
            relation = form.relation.data,
            fname = form.fname.data,
            lname = form.lname.data,
            mobile = form.mobile.data,
            altphone = form.altphone.data,
            email = form.email.data,
            altemail = form.altemail.data,
            street = form.street.data,
            city = form.city.data,
            state = form.state.data,
            zipcode = form.zipcode.data,
            notes = form.notes.data,
            primarylang = form.primarylang.data,
            needstranslation = form.needstranslation.data
        )
        # editUser.adults.filter(oid=adultoid).save()
        editUser.save()
        # Record edit datetime to user record
        userModified(editUser)

        return redirect(url_for('profile', aeriesid=aeriesid))

    form.preferredcontact.data = editAdult.preferredcontact
    form.relation.data = editAdult.relation
    form.fname.data = editAdult.fname
    form.lname.data = editAdult.lname
    form.mobile.data = editAdult.mobile
    form.altphone.data = editAdult.altphone
    form.email.data  = editAdult.email
    form.altemail.data  = editAdult.altemail
    form.street.data  = editAdult.street
    form.city.data  = editAdult.city
    form.state.data = editAdult.state
    form.zipcode.data = editAdult.zipcode
    form.notes.data = editAdult.notes
    form.primarylang.data = editAdult.primarylang
    form.needstranslation.data = editAdult.needstranslation

    return render_template('editadult.html',form=form,editUser=editUser,editAdult=editAdult)

@app.route('/deleteadult/<aeriesid>/<adultoid>')
def deleteadult(aeriesid,adultoid):
    editUser = User.objects.get(aeriesid=aeriesid)
    editAdult = editUser.adults.get(oid=adultoid)
    flash(f"Adult record {editAdult.oid} {editAdult.fname} {editAdult.lname} was deleted")
    editUser.adults.filter(oid=adultoid).delete()
    editUser.adults.filter(oid=adultoid).save()
    # Record edit datetime to user record
    userModified(editUser)
    
    return redirect(url_for('profile', aeriesid=aeriesid))

@app.route('/postgradnew/<uid>', methods=['POST','GET'])
def postgradnew(uid):

    stu = User.objects.get(pk=uid)
    form = PostGradForm()

    if form.validate_on_submit():
        stu.postgrads.create(
            oid = ObjectId(),
            type_ = form.type_.data,
            org = form.org.data,
            link = form.link.data,
            major = form.major.data,
            graduated = form.graduated.data,
            desc = form.desc.data,
            yr_started = form.yr_started.data,
            yr_ended = form.yr_ended.data,
            pg_st_address = form.pg_st_address.data,
            pg_city = form.pg_city.data,
            pg_state = form.pg_state.data,
            pg_zip = form.pg_zip.data
            )
        stu.save()
        return redirect(url_for("profile", aeriesid=stu.aeriesid))

    return render_template("postgradform.html",form=form)

@app.route('/postgradedit/<uid>/<pgid>', methods=['GET','POST'])
def postgradedit(uid,pgid):

    editStu = User.objects.get(pk=uid)
    editPG = editStu.postgrads.get(oid=pgid)
    form = PostGradForm()

    if form.validate_on_submit():
        editStu.postgrads.filter(oid=pgid).update(
            type_ = form.type_.data,
            org = form.org.data,
            link = form.link.data,
            major = form.major.data,
            graduated = form.graduated.data,
            desc = form.desc.data,
            yr_started = form.yr_started.data,
            yr_ended = form.yr_ended.data,
            pg_st_address = form.pg_st_address.data,
            pg_city = form.pg_city.data,
            pg_state = form.pg_state.data,
            pg_zip = form.pg_zip.data
        )
        editStu.save()

        return redirect(url_for('profile',aeriesid=editStu.aeriesid))

    form.type_.data = editPG.type_
    form.org.data = editPG.org
    form.link.data = editPG.link
    form.major.data = editPG.major
    form.graduated.data = editPG.graduated
    form.desc.data = editPG.desc
    form.yr_started.data = editPG.yr_started
    form.yr_ended.data = editPG.yr_ended
    form.pg_st_address.data = editPG.pg_st_address
    form.pg_city.data = editPG.pg_city
    form.pg_state.data = editPG.pg_state
    form.pg_zip.data = editPG.pg_zip

    return render_template("postgradform.html",form=form)


@app.route('/postgraddelete/<uid>/<pgid>')
def postgraddelete(uid,pgid):
    editStu = User.objects.get(pk=uid)
    editPG = editStu.postgrads.get(oid=pgid)
    name=editPG.org
    editStu.postgrads.filter(oid=pgid).delete()
    flash(f"Post Grad record {name} was deleted")

    editStu.save()
    
    return redirect(url_for('profile', aeriesid=editStu.aeriesid))

#######################################################################################
### THE CODE BELOW IS ALL GOOGLE AUTHENTICATION CODE AND PROBABLY SHOULD NOT BE TOUCHED

# Do not edit anything in this route.  This is just for google authentication
@app.route('/authorize')
def authorize():

    # Log user in with the appropriate privledges / scopes from google based on the audience they belong to.
    try:
        audience = session['audience']
    except:
        session['audience'] = None
        print("No audience")
    else:
        if session['audience'] == 'ot':
            flash(f"you have logged in as OT")
            SCOPES = SCOPESOT
        elif session['audience'] == 'community':
            flash(f"You have logged in as Community")
            SCOPES = SCOPESCOMMUNITY
        else:
            flash(f"You have not designated an audience (OT or Community).")
            print(f"You have not designated an audience (OT or Community).")
            return redirect('/')

    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config=GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES)

    # The URI created here must exactly match one of the authorized redirect URIs
    # for the OAuth 2.0 client, which you configured in the API Console. If this
    # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
    # error.
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true',
        # Force the Google Account picker even if there is only one account. This is 
        # because a user can login as a non-ousd user but not be allowed access to anything
        # so it becomes difficult to login with an OUSD account after that if you have one.
        # prompt='select_account consent'
        prompt='select_account'
        )

    # Store the state so the callback can verify the auth server response.
    session['state'] = state
    #session['expires_in'] = expires_in

    return redirect(authorization_url)

# Do not edit anything in this route.  This is just for google authentication
@app.route("/oauth2callback")
def oauth2callback():

    try:
        if session['audience'] == 'ot':
            SCOPES = SCOPESOT
        elif session['audience'] == 'community':
            SCOPES = SCOPESCOMMUNITY
        else:
            flash(f"You have not designated an audience (OT or Community).")
            print(f"You have not designated an audience (OT or Community).")
    except:
        session['audience'] = None
        flash("No audience")

    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = session['state']

    # flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config=GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = request.url

    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

    #return flask.redirect(flask.url_for('test_api_request'))
    return redirect(url_for('login'))

# Do not edit anything in this route.  This is just for google authentication
@app.route('/revoke')
def revoke():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')

    session['credentials'] = credentials_to_dict(credentials)

    revoke = requests.post('https://accounts.google.com/o/oauth2/revoke',
        params={'token': credentials.token},
        headers = {'content-type': 'application/x-www-form-urlencoded'})

    status_code = getattr(revoke, 'status_code')
    if status_code == 200:
        session['revokereq']=1
        flash(Markup(f"Revoke request has been processed. You can now <a href='/logout'>logout.</a>"))
        return redirect('/')
        #return redirect('/logout')
    else:
        flash('An error occurred when trying to revoke the privledges you granted to Google.')
        return redirect('/')


@app.route("/logout")
def logout():
    session.clear()
    flash('Session has been cleared and user logged out.')
    return redirect('/')

@app.route('/privacy')
def privacy():
    return render_template('privacypolicy.html')