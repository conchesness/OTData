from app import app
from flask import render_template, redirect, session, flash, url_for
from app.classes.data import User, Help
# from app.classes.forms import 
from datetime import datetime as dt
from datetime import timedelta
from mongoengine import Q


@app.route('/createhelp')
def help():
    currUser = User.objects.get(gid=session['gid'])
    newHelp = Help(
        requester = currUser,
        status = 'asked'
    )
    newHelp.save()
    return redirect(url_for('checkin'))

@app.route('/offerhelp/<helpid>')
def offerhelp(hepid):

    pass

@app.route('/confirmhelp/<helpid>')
def confirmhelp(helpid):
     
    pass