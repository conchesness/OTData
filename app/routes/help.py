from app.classes.forms import ActiveClassesForm, SimpleForm
from app import app
from flask import render_template, redirect, session, flash, url_for
from app.classes.data import GoogleClassroom, User, Help, Token
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

    if currUser == offerHelp.requester:
        flash("You can't be the helper AND the help requester.")
        return redirect(url_for('checkin'))

    if offerHelp.helper:
        flash("There is already a helper for this help.")
        return redirect(url_for('checkin'))

    offerHelp.update(
        helper = currUser,
        status = "offered",
        offered = dt.utcnow()
    )

 
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

    return redirect(url_for('checkin'))


@app.route('/help/confirm/<helpid>', methods=['GET', 'POST'])
def confirmhelp(helpid):
        
    confirmHelp = Help.objects.get(pk=helpid)
    currUser = User.objects.get(gid=session['gid'])
    form = SimpleForm()

    if currUser.role.lower() == "teacher" and not confirmHelp.helper:
        confirmHelp.update(
            helper = currUser
        )
        confirmHelp.reload()

    if confirmHelp.requester != currUser and currUser.role.lower() != "teacher":
        flash('You can only confirm a help that you have requested.')
        return redirect(url_for('checkin'))

    if not confirmHelp.helper:
        flash('You can only confirm a help where there is a helper.')
        return redirect(url_for('checkin'))

    if confirmHelp.status == "confirmed":
        flash('This help is already confirmed.')
        return redirect(url_for('checkin'))

    if currUser.role.lower() == 'student' and not form.validate_on_submit():
        return render_template('confirmform.html',form=form)
    
    confirmHelp.update(
        confirmed = dt.utcnow(),
        status = "confirmed",
        confirmdesc = form.field.data
    )
    banker = User.objects.get(otemail='stephen.wright@ousd.org')
    # give the help requester a Token for requesting a help that is now confirmed
    requester1 = Token(
        giver = banker,
        owner = confirmHelp.requester,
        help = confirmHelp
    )
    requester1.save()

    # If the help was confirmed by the requester, give them another token
    if currUser == confirmHelp.requester:
        requester2 = Token(
            giver = banker,
            owner = confirmHelp.requester,
            help = confirmHelp
        )
        requester2.save()

    # If the helper is a student, give them a token
    if confirmHelp.helper.role.lower() == "student":
        helper1 = Token(
            giver = banker,
            owner = confirmHelp.helper,
            help = confirmHelp
        )
        helper1.save()

    return redirect(url_for('checkin'))


@app.route('/help/delete/<helpid>')
def deletehelp(helpid):

    delHelp = Help.objects.get(pk=helpid)
    currUser = User.objects.get(gid=session['gid'])

    if currUser.role.lower() == "teacher":
        delHelp.delete()
        flash('The requested Help is deleted.')
        return redirect(url_for('checkin'))

    if currUser != delHelp.requester:
        flash('You are not the requester of the help so you cannot delete it.')
        return redirect(url_for('checkin'))

    if delHelp.status == "confirmed":
        flash("You can't delete a confirmed help.")
        return redirect(url_for('checkin'))

    delHelp.delete()
    flash('Your requested Help is deleted.')

    return redirect(url_for('checkin'))