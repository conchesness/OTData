from app import app
from .scopes import *

from flask import render_template, redirect, url_for, request, session, flash, Markup
from app.classes.data import User, Config, Adult
from app.classes.forms import UserForm, AdultForm
from .credentials import GOOGLE_CLIENT_CONFIG
from requests_oauth2.services import GoogleClient
from requests_oauth2 import OAuth2BearerToken
from mongoengine import Q
from bson.objectid import ObjectId
import requests
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import os


# List of email addresses for Admin users
admins = ['stephen.wright@ousd.org']

# This code is run right after the app starts up and then not again. It defines a few universal things
# like is the app being run on a local computer and what is the local timezone
@app.before_first_request
def before_first_request():
    settings = Config.objects.first()
    if not settings:
        settings = Config(devenv=True,localtz='nada')
        settings.save()
        settings.reload()

    if request.url_root[8:11] == '127' or request.url_root[8:17] == 'localhost':
        settings.update(devenv = True, localtz='America/Los_Angeles')
    else:
        settings.update(devenv = False, localtz='UTC')

# This runs before every route and serves to make sure users are using a secure site and can only
# access pages they are allowed to access
@app.before_request
def before_request():
    
    # this checks if the user requests http and if they did it changes it to https
    if not request.is_secure:
        url = request.url.replace("http://", "https://", 1)
        code = 301
        return redirect(url, code=code)

    # Create a list of all the paths that do not need authorization or are part of authorizing
    # so that each path this is *not* in this list requires an authorization check.
    # If you have urls that you want your user to be able to see without logging in add them here.
    unauthPaths = ['/','/home','/authorize','/login','/oauth2callback', '/static/favicon.ico', '/static/local.css','/logout','/revoke']   
    studentPaths = ['/profile','/editprofile','/addadult','/editadult','/deleteadult'] 
    # this is some tricky code designed to send the user to the page they requested even if they have to first go through
    # a authorization process.
    try: 
        session['return_URL']
    except:
        session['return_URL'] = '/'
    
    if request.path not in unauthPaths:
        session['return_URL'] = request.full_path
        if session['role'].lower() == 'student' and request.path not in studentPaths:
            # Send students to their profile page
            return redirect(url_for('profile'))

    # this sends users back to authorization if the login has timed out or other similar stuff
    if request.path not in unauthPaths:
        if 'credentials' not in session:
            return redirect(url_for('authorize'))
        if not google.oauth2.credentials.Credentials(**session['credentials']).valid:
            return redirect(url_for('authorize'))
        else:
            # refresh the session credentials
            credentials = google.oauth2.credentials.Credentials(**session['credentials'])
            session['credentials'] = credentials_to_dict(credentials)

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
    except:
        currUser=None

    return render_template("index.html", announceBody=announceBody, announcement=announcement, currUser=currUser)


# a lot of stuff going on here for the user as they log in including creatin new users if this is their first login
@app.route('/login')
def login():

    # Go and get the users credentials from google. The /authorize and /oauth2callback functions should not be edited.
    # That is where the user is sent if their credentials are not currently stored in the session.  More about sessions below. 
    if 'credentials' not in session:
        # send a msg to the user
        # send the user to get authenticated by google
        return redirect(url_for('authorize'))

    # Now that the user has credentials, use those credentials to access Google's people api and get the users information
    credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    session['credentials'] = credentials_to_dict(credentials)
    people_service = googleapiclient.discovery.build('people', 'v1', credentials=credentials)
    # set data to be the dictionary that contains all the information about the user that google has.  You can see this 
    # information displayed via the current profile template
    data = people_service.people().get(resourceName='people/me', personFields='names,emailAddresses,photos').execute()

    if data['emailAddresses'][0]['value'][-8:] == "ousd.org" and data['emailAddresses'][0]['value'][0:2] == "s_":
        session['role'] = 'Student'
    else:
        session['role'] = 'Teacher'

    if data['emailAddresses'][0]['value'] in admins:
        session['isadmin'] = True
    else:
        session['isadmin'] = False

    try:
        currUser = User.objects.get(otemail = data['emailAddresses'][0]['value'])
        # if currUser.role == "Student":
        #     flash('Students cannot yet access this site.')
    except:
        flash(f'You are not in the database.  Please contact Steve Wright to get access. stephen.wright@ousd.org')
        return redirect('/')

    if not currUser.gid:
        currUser.update(
            gid=data['emailAddresses'][0]['metadata']['source']['id'],
            role=session['role'],
            isadmin=session['isadmin'] 
        )
        currUser.reload()

    # Set the session variables
    settings = Config.objects.first()
    session['devenv'] = settings.devenv
    session['localtz'] = settings.localtz
    if currUser.ufname:
        session['fname']=currUser.ufname
    else:
        session['fname']=currUser.afname
    if currUser.ulname:
        session['lname']=currUser.ulname
    else:
        session['lname']=currUser.alname

    flash(f"Hello {session['fname']}")

    session['displayName'] = f"{session['fname']} {session['lname']}"
    session['currUserId'] = str(currUser.id)
    session['aeriesid'] = currUser.aeriesid
    session['gid'] = currUser.gid
    # this stores the entire Google Data object in the session
    session['gdata'] = data
    session['role'] = currUser.role
    session['isadmin'] = currUser.isadmin

    # except:
    #     flash(f'Please contact Mr. Wright (stephen.wright@ousd.org) and let him know you need an an account on OTData.')
    #     return redirect('/')


    # The return_URL value is set above in the before_request route. This enables a user you is redirected to login to
    # be able to be returned to the page they originally asked for.
    return redirect(session['return_URL'])

#This is the profile page for the logged in user
@app.route('/profile/<aeriesid>')
@app.route('/profile')
def profile(aeriesid=None):
    if session['role'] == "Student":
        return render_template('/profile')
    elif aeriesid and session['role'] != "Student":
        try:
            targetUser = User.objects.get(aeriesid=aeriesid)
        except:
            flash(f"Aeries ID {aeriesid} is not in the database, displaying your profile instead. Contact Steve Wright if you feel this is an error (stephen.wright@ousd.org).")
            targetUser=User.objects.get(gid=session['gid'])
    else:
        try:
            targetUser=User.objects.get(gid=session['gid'])
        except:
            flash(f"Aeries ID {aeriesid} is not in the database, displaying your profile instead. Contact Steve Wright if you feel this is an error (stephen.wright@ousd.org).")
            targetUser=User.objects.get(gid=session['gid'])        
    #Send the user to the profile.html template

    if targetUser.ufname:
        fname = targetUser.ufname
    else:
        fname = targetUser.afname

    if targetUser.ulname:
        lname = targetUser.ulname
    else:
        lname = targetUser.alname

    targetUser.fullName = f"{fname} {lname}"

    return render_template("profile.html", currUser=targetUser, data=session['gdata'])

# to get an in depth description of how creating, editing and deleting database recodes work check
# out the feedback.py file.
# This route anables the current user to edit some values in their profile.
@app.route('/editprofile/<aeriesid>', methods=['GET', 'POST'])
def editprofile(aeriesid):

    # create a form object from the UserForm Class
    form = UserForm()
    # get the user object that is going to be edited which will be the current user so we user the 
    # googleId from the active session to load the right record
    if aeriesid == session['aeriesid'] or aeriesid == 'None':
        editUser = User.objects.get(gid=session['gid'])
    elif session['role'] != 'Student':
        editUser = User.objects.get(aeriesid=aeriesid)
    else:
        flash(f"You do not have access to edit this user's profile.")
        return redirect(url_for(profile, aeriesid=aeriesid))

    # If the user has already submitted the edit form and it is valid the the method form.validate_on_submit()
    # will be True and we can take the values from the form object and use them to update the database record 
    # for that user
    if form.validate_on_submit():
        if not form.mobile.data:
            form.mobile.data = None
        editUser.update(
            # the values to the left are the data attributes from the User data class
            # the values to the right are the values the user submitted via the form 
            # that wtforms puts in to the form object
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
        )
        if form.image.data:
            editUser.image.delete()
            editUser.image.put(form.image.data, content_type = 'image/jpeg')
            editUser.save()

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
    form.altphone.data = editUser.altphone
    form.uethnicity.data = editUser.uethnicity
    form.uethnicityother.data = editUser.uethnicityother
    form.ugender.data = editUser.ugender

    # render the editprofile template and send the pre-populated form object.
    return render_template('editprofile.html', form=form, editUser=editUser)

@app.route('/addadult/<aeriesid>', methods=['GET', 'POST'])
def addadult(aeriesid):
    editUser = User.objects.get(aeriesid = aeriesid)
    form = AdultForm()
    if not form.mobile.data:
        form.mobile.data = None
    if not form.altphone.data:
        form.altphone.data = None
    if form.validate_on_submit():

        editUser.adults.create(
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
                notes = form.notes.data
            )
        editUser.save()
        return redirect(url_for('profile', aeriesid=aeriesid))

    return render_template('editadult.html',form=form,editUser=editUser)

@app.route('/editadult/<aeriesid>/<adultoid>', methods=['GET', 'POST'])
def editadult(aeriesid,adultoid):
    editUser = User.objects.get(aeriesid=aeriesid)
    editAdult = editUser.adults.get(oid=adultoid)

    form = AdultForm()

    if form.validate_on_submit():

        # different syntax for updating an Embedded Document. replace the fields then save to parent doc.
        editUser.adults.filter(oid=adultoid).update(
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
            notes = form.notes.data
        )

        editUser.adults.filter(oid=adultoid).save()

        return redirect(url_for('profile', aeriesid=aeriesid))

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

    return render_template('editadult.html',form=form,editUser=editUser,editAdult=editAdult)

@app.route('/deleteadult/<aeriesid>/<adultoid>')
def deleteadult(aeriesid,adultoid):
    editUser = User.objects.get(aeriesid=aeriesid)
    editAdult = editUser.adults.get(oid=adultoid)
    flash(f"Adult record {editAdult.oid} {editAdult.fname} {editAdult.lname} was deleted")
    editUser.adults.filter(oid=adultoid).delete()
    editUser.adults.filter(oid=adultoid).save()
    
    return redirect(url_for('profile', aeriesid=aeriesid))

    
#######################################################################################
### THE CODE BELOW IS ALL GOOGLE AUTHENTICATION CODE AND PROBABLY SHOULD NOT BE TOUCHED

# Do not edit anything in this route.  This is just for google authentication
@app.route('/authorize')
def authorize():

    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    # flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)

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
        prompt='select_account consent'
        )

    # Store the state so the callback can verify the auth server response.
    session['state'] = state
    #session['expires_in'] = expires_in

    return redirect(authorization_url)

# Do not edit anything in this route.  This is just for google authentication
@app.route("/oauth2callback")
def oauth2callback():
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
        return redirect('authorize')

    revoke = requests.post('https://accounts.google.com/o/oauth2/revoke',
        params={'token': credentials.token},
        headers = {'content-type': 'application/x-www-form-urlencoded'})

    status_code = getattr(revoke, 'status_code')
    if status_code == 200:
        session['revokereq']=1
        return redirect('/logout')
    else:
        flash('An error occurred.')
        return redirect('/')


@app.route("/logout")
def logout():
    session.clear()
    flash('Session has been cleared and user logged out.')
    return redirect('/')

# Do not edit anything in this route.  This is just for google authentication
def credentials_to_dict(credentials):
    return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes
          }

