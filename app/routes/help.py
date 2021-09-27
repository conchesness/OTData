from app.classes.forms import ActiveClassesForm
from app import app
from flask import render_template, redirect, session, flash, url_for
from app.classes.data import GoogleClassroom, User, Help
from app.classes.forms import ActiveClassesForm
from datetime import datetime as dt
from datetime import timedelta
from mongoengine import Q


@app.route('/help/create', methods=['GET', 'POST'])
def createhelp():

    form = ActiveClassesForm()
    currUser = User.objects.get(gid=session['gid'])
    gCourses = currUser.gclasses
    gclasses = []

    for gCourse in gCourses:
        if gCourse.gclassroom:
            tempname = gCourse.gclassroom.gclassdict['name']
            if not gCourse.status:

                gCourse.status = ""

            # a list of tuples for the form
            if gCourse.status == "Active":
                gclasses.append((gCourse.gclassroom.gclassid, tempname))

    form.gclassid.choices = gclasses

    if form.validate_on_submit():

        gclass = GoogleClassroom.objects.get(gclassid = form.gclassid.data)

        newHelp = Help(
            requester = currUser,
            status = 'asked',
            gclass = gclass
        )
        newHelp.save()

        return redirect(url_for('checkin'))

    return render_template('helpform.html', currUser=currUser, form=form)

@app.route('/help/offer/<helpid>')
def offerhelp(helpid):

    offerHelp = Help.objects.get(pk=helpid)
    currUser = User.objects.get(gid=session['gid'])
    if currUser != offerHelp.requester and not offerHelp.helper:
        offerHelp.update(
            helper = currUser,
            status = "offered",
            offered = dt.datetime.utcnow()
        )
    else:
        flash("Can't add you as the helper.")
 
    return redirect(url_for('checkin'))

@app.route('/help/recind/<helpid>')
def helprecind(helpid):
    recindHelp = Help.objects.get(pk=helpid)
    currUser = User.objects.get(gid=session['gid'])
    if currUser == recindHelp.helper:
        recindHelp.update(
            helper = None,
            status = "asked",
            offered = None
        )
        flash('Offer has been recinded.')
    else:
        flash("Offer can't be recinded because you are not the Helper.")

@app.route('/help/confirm/<helpid>')
def confirmhelp(helpid):
     
    pass

@app.route('/help/delete/<helpid>')
def deletehelp(helpid):

    delHelp = Help.objects.get(pk=helpid)
    currUser = User.objects.get(gid=session['gid'])

    if currUser == delHelp.requester:
        delHelp.delete()
        flash('Your requested Help is deleted.')
    else:
        flash('You are not the requester of the help so you cannot delete it.')

    return redirect(url_for('checkin'))