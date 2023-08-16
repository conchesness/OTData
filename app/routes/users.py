#from app.routes.coursecat import course
from app import app
from .scopes import scopes_ousd
from flask import render_template, redirect, url_for, request, session, flash, Markup
from app.classes.data import User, CheckIn, Group, Message, Token
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
import time
from flask_login import current_user

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
    currUser = current_user
    editUser.lastedited.append([dt.datetime.utcnow(),currUser]) 
    if len(editUser.lastedited) > 20:
        editUser.lastedited.pop(0)

    if editUser.ustreet:
        street = editUser.ustreet
    else:
        street = editUser.astreet

    if editUser.ucity:
        city = editUser.ucity
    else:
        city = editUser.acity

    if editUser.ustate:
        state = editUser.ustate
    else:
        state = editUser.astate

    if editUser.uzipcode:
        zipcode = editUser.uzipcode
    else:
        zipcode = editUser.azipcode

    url = f"https://nominatim.openstreetmap.org/search?street={street}&city={city}&state={state}&postalcode={zipcode}&format=json&addressdetails=1&email=stephen.wright@ousd.org"
    r = requests.get(url)

    try:
        r = r.json()
    except:
        pass
    else:
        if len(r) != 0:
            editUser.lat = float(r[0]['lat'])
            editUser.lon = float(r[0]['lon'])
            flash('Updated lat/lon')

    flash('User edited.')

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

# # This runs before every route and serves to make sure users are using a secure site and can only
# # access pages they are allowed to access
# @app.before_request
# def before_request():

#     try:
#         if session['isadmin']:
#             db = get_db()
#             session['db'] = db.name
#     except:
#         pass

#     # this checks if the user requests http and if they did it changes it to https
#     if not request.is_secure:
#         url = request.url.replace("http://", "https://", 1)
#         code = 301
#         return redirect(url, code=code)

#     # Create a list of all the paths that do not need authorization or are part of authorizing
#     # so that each path this is *not* in this list requires an authorization check.
#     # If you have urls that you want your user to be able to see without logging in add them here.
#     # TODO create a decorator or something for this
#     # TODO could just prefix the url with "/stu/" for studentpaths
#     unauthPaths = ['/','/home','/authorize','/login','/oauth2callback','/static','/logout','/revoke','/msgreply','/msgstatus']   
#     studentPaths = ['/transcript','/project','/myprojects','/getgclasses','/comp/','/compborrow','/student','/breaks','/classdash','/assignments','/help','/breakstart','/postgrad','/cc','/plan','/profile','/editprofile','/addadult','/editadult','/deleteadult','/sendstudentemail','/checkin','/deletecheckin','/editgclass','/deletegclass','/gclasses','/missingassignmentsstu'] 
#     # this is some tricky code designed to send the user to the page they requested even if they have to first go through
#     # a authorization process.
#     try: 
#         session['return_URL']
#     except:
#         session['return_URL'] = '/'

#     # find the first path argument in the URL
#     basePath = request.path
#     basePath = basePath.split('/')
#     basePath = '/'+basePath[1]

#     # this sends users back to authorization if the login has timed out or other similar stuff
#     if basePath not in unauthPaths:
#         session['return_URL'] = request.path
#         if 'credentials' not in session:
#             flash(f'Adding credentials to session')
#             return redirect(url_for('authorize'))
#         if not google.oauth2.credentials.Credentials(**session['credentials']).valid:
#             flash('session credentials not valid')
#             return redirect(url_for('authorize'))
#         else:
#             # refresh the session credentials
#             if google.oauth2.credentials.Credentials(**session['credentials']).valid:
#                 credentials = google.oauth2.credentials.Credentials(**session['credentials'])
#             else:
#                 return redirect('/authorize')
#             session['credentials'] = credentials_to_dict(credentials)
#             # reset the return_URL
#             session['return_URL'] = request.full_path
#             if session['role'].lower() == 'student':
#                 for studentPath in studentPaths:
#                     match = re.match(f"{studentPath}.*", basePath)
#                     if match:
#                         return

#             if session['role'].lower() == 'student':
#                 # Send students to their profile page
#                 flash(f"Unfortunately, you do not have access to the url '{basePath}'.")
#                 return redirect(url_for('profile'))
                
# This tells the app what to do if the user requests the home either via '/home' or just'/'
@app.route('/home')
@app.route('/')
def index():
    #get the curent requesting this page but include error handling because the user might not be logged in
    try: 
        currUser = current_user
        # If this is a student, send them to their profile page
        try:
            if session['role'].lower() == 'student':
                return redirect(url_for('profile',aeriesid=currUser.aeriesid))
        except:
            #TODO: need to get rid of aeiresid
            pass
    except:
        currUser=None
    return render_template("index.html", currUser=currUser)


#get the profile page for a designated or the logged in user. Can use either gid or aeriesid.
#TODO change this to GID instead of AeriesId so Teacher profiles can be accessed
@app.route('/profile/<aeriesid>', methods=['GET', 'POST'])
@app.route('/profile', methods=['GET', 'POST'])
def profile(aeriesid=None):

    if aeriesid == 'None':
        aeriesid = None 

    if current_user.role.lower() != "teacher":
        targetUser = User.objects.get(id = current_user.id)
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
            targetUser=User.objects.get(gid=current_user.gid)
    else:
        try:
            targetUser=User.objects.get(gid=current_user.gid)
        except:
            flash("You are not in the database of users which doesn't make sense cause you're already looged in. Sorry this shouldn't ever happen. (stephen.wright@ousd.org).")
            return redirect('/')

    if targetUser.role.lower() == "student":
        checkins = CheckIn.objects(student=targetUser).limit(15)
        #messages = Message.objects(student=targetUser).limit(6)
        tokens = Token.objects(owner=targetUser)
    else:
        checkins = None
        tokens = None

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

    if current_user.role.lower()!='student':
        groups = Group.objects(owner=current_user)
    else:
        groups=None

    return render_template("profile/profile.html",groups=groups,currUser=targetUser, data=session['gdata'], form=form, today=dttoday, checkins=checkins, tokens=tokens)

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

        editUser.reload()

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

@app.route('/privacy')
def privacy():
    return render_template('privacypolicy.html')