
# Python standard libraries
import json
from app import app, login_manager
from flask import redirect, request, url_for, flash, session
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from oauthlib.oauth2 import WebApplicationClient
import google_auth_oauthlib.flow
import requests
from app.classes.data import User
from app.utils.secrets import getSecrets
import mongoengine.errors
from .scopes import scopes_ousd
from .credentials import GOOGLE_CLIENT_CONFIG
import requests

#get all the credentials for google
secrets = getSecrets()

admins = ["stephen.wright@ousd.org"]

# OAuth2 client setup
client = WebApplicationClient(secrets['GOOGLE_CLIENT_ID'])

# When a route is decorated with @login_required and fails this code is run
# https://flask-login.readthedocs.io/en/latest/#flask_login.LoginManager.unauthorized_handler
@login_manager.unauthorized_handler
def unauthorized():
    flash("You must be logged in to access that content.")
    return redirect(url_for('index'))

# Flask-Login helper to retrieve a user object from our db
# https://flask-login.readthedocs.io/en/latest/#flask_login.LoginManager.user_loader
@login_manager.user_loader
def load_user(id):
    try:
        return User.objects.get(pk=id)
    except mongoengine.errors.DoesNotExist:
        flash("Something strange has happened. This user doesn't exist. Please click logout.")
        return redirect(url_for('index'))

def get_google_provider_cfg():
    return requests.get(secrets['GOOGLE_DISCOVERY_URL']).json()

@app.route("/login")
def login():
    
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
        prompt="select_account"
    )

    return redirect(request_uri)


@app.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    session['code'] = request.args.get("code")
    code = session['code']


    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code,
    )

    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(secrets['GOOGLE_CLIENT_ID'], secrets['GOOGLE_CLIENT_SECRET']),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Now that we have tokens (yay) let's find and hit URL
    # from Google that gives you user's profile information,
    # including their Google Profile Image and Email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    ### Example info that comes back from google
    # userinfo_response.json() --> {
    # 'sub': '118043475517321263044', 
    # 'name': 'STEPHEN WRIGHT', 
    # 'given_name': 'STEPHEN', 
    # 'family_name': 'WRIGHT', 
    # 'profile': 'https://plus.google.com/118043475517321263044', 
    # 'picture': 'https://lh3.googleusercontent.com/a-/AOh14GiaVFKJoTd0DhTprTOa4K9Smeeaucy9ksWQx18FOA=s96-c', 
    # 'email': 'stephen.wright@ousd.org', 
    # 'email_verified': True, 
    # 'locale': 'en', 
    # 'hd': 'ousd.org'
    # }

    session['gdata'] = userinfo_response.json()

    if userinfo_response.json().get("hd") != "ousd.org":
        flash("You must have an ousd.org email account to access this site.")
        return "You must have an ousd.org email account to access this site.", 400

    # We want to make sure their email is verified.
    # The user authenticated with Google, authorized our
    # app, and now we've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        gid = userinfo_response.json()["sub"]
        gmail = userinfo_response.json()["email"]
        gprofile_pic = userinfo_response.json()["picture"]
        gname = userinfo_response.json()["name"]
        gfname = userinfo_response.json()["given_name"]
        glname = userinfo_response.json()["family_name"]
    else:
        return "User email not available or not verified by Google.", 400

    # Get user from DB or create new user
    try:
        thisUser=User.objects.get(oemail=gmail)
    except mongoengine.errors.DoesNotExist:
        if userinfo_response.json().get("hd") == "ousd.org":
            thisUser = User(
                gid=gid, 
                gname=gname, 
                oemail=gmail, 
                gprofile_pic=gprofile_pic,
                fname = gfname,
                lname = glname
            )
            thisUser.save()
            thisUser.reload()
        else:
            flash("You must have an ousd.org email to login to this site.")
            return redirect(url_for('index'))
    else:
        thisUser.update(
            gid=gid, 
            gname=gname, 
            gprofile_pic=gprofile_pic,
            fname = gfname,
            lname = glname
        )
    thisUser.reload()

    # Begin user session by logging the user in
    login_user(thisUser)

    # Send user back to homepage
    return redirect(url_for("index"))

@app.route("/logout")
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for("index"))

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

# Do not edit anything in this function.  This is just for google authentication
def credentials_to_dict(credentials):
    return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes
          }

@app.route('/authorize')
def authorize():
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config=GOOGLE_CLIENT_CONFIG,
        scopes=scopes_ousd)

    # The URI created here must exactly match one of the authorized redirect URIs
    # for the OAuth 2.0 client, which you configured in the API Console. If this
    # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
    # error.
    flow.redirect_uri = url_for('callback', _external=True)


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
        prompt='select_account')

    #now turn those parameters into a token.
    flow.fetch_token(authorization_response=request.url)

    # Store the state so the callback can verify the auth server response.
    session['state'] = state
    session['credentials'] = flow.credentials

    return redirect(authorization_url)