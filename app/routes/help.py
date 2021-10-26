from app.classes.forms import ActiveClassesForm, SimpleForm
from app import app
from flask import render_template, redirect, session, flash, url_for
from app.classes.data import GoogleClassroom, User, Help, Token
from app.classes.forms import ActiveClassesForm
from datetime import datetime as dt
from datetime import timedelta
from mongoengine import Q
import mongoengine.errors


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
    isStuList = False
    if form.validate_on_submit():
        gclass = GoogleClassroom.objects.get(gclassid = form.gclassid.data)

        if not form.students.data:
            stuGIdList = [('----','Anyone'),(gclass.gteacherdict['id'],f"Mr. {gclass.gteacherdict['name']['familyName']}")]
            try:
                gclass.groster['roster']
            except:
                flash("There is no available roster for this class. This can only\
                    be created by the teacher.")
            else:
                for stu in gclass.groster['roster']:
                    stuName = f"{stu['profile']['name']['givenName']} {stu['profile']['name']['familyName']}"
                    if stu['sortCohort']:
                        stuName = f"{stu['sortCohort']} {stuName}"
                    stuGIdList.append((stu['userId'],stuName))
                stuGIdList.sort(key=lambda tup: tup[1]) 
            form.students.choices = stuGIdList
            isStuList = True
        else:
            newHelp = Help(
                requester = currUser,
                status = 'asked',
                gclass = gclass
            )
            newHelp.save()
            if form.students.data != '----':
                try:
                    reqHelper = User.objects.get(gid = form.students.data)
                except mongoengine.errors.DoesNotExist as error:
                    flash("The user you are looking for does not exist in the database. \
                           Ask them to sign in which will make them avaialble. The help \
                           was created but no one was specifically requested as the helper.")
                else:
                    newHelp.update(reqhelper = reqHelper)

            return redirect(url_for('checkin'))

    return render_template('helpform.html', currUser=currUser, form=form, isStuList = isStuList)

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

@app.route('/dashboard/<gclassid>')
def dashboard(gclassid):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    helps = Help.objects(gclass=gClassroom)

    return render_template('classdashboard.html', helps=helps)

@app.route('/approvehelp/<helpid>')
def approvehelp(helpid):
    help = Help.objects.get(pk=helpid)
    help.update(status='approved')
    
    return redirect(url_for('dashboard',gclassid=help.gclass.gclassid))

@app.route('/rejecthelp/<helpid>')
def rejecthelp(helpid):
    help = Help.objects.get(pk=helpid)
    help.update(
        status = 'rejected',
        note = 'Rejected for bad or missing confirmation description.'
        )
    help.reload()

    tokens = Token.objects(owner = help.requester).sum('amt')
    if tokens > 0:
        Token.objects(owner = help.requester).first().delete()
        note=help.note+" One Token was deleted from your account."
        help.update(note=note)
    else:
        note=help.note+" I looked to delete a token from your account but you had none."

    
    return redirect(url_for('dashboard',gclassid=help.gclass.gclassid))

@app.route('/approveallconfirmed/<gclassid>')
def approveallconfirmed(gclassid):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    helps = Help.objects(gclass=gClassroom,status='confirmed')
    helps.update(status='approved')
    helps = Help.objects(gclass=gClassroom)

    return render_template('classdashboard.html', helps=helps)