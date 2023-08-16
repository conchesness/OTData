from app.classes.forms import ActiveClassesForm, SimpleForm, TokenForm
from app import app
from flask import render_template, redirect, session, flash, url_for, Markup
from app.classes.data import GEnrollment, GoogleClassroom, User, Help, Token
from app.classes.forms import ActiveClassesForm
from datetime import datetime as dt
#from datetime import timedelta
from mongoengine import Q
import mongoengine.errors
from .msgs import txtOneStu
from flask_login import current_user

@app.route('/help/create/<gclassid>', methods=['GET', 'POST'])
def createhelp(gclassid):

    currUser = current_user
    gClass = GoogleClassroom.objects.get(gclassid=gclassid)
    query = Q(requester=currUser) & Q(gclass=gClass) & (Q(status = 'asked') | Q(status = 'offered'))
    lastHelp = Help.objects(query)
    if len(lastHelp) > 0:
        flash('You have an open help for this class. Delete or complete that Help first.')
        return redirect(url_for('classdash',gclassid=gclassid))

    form = ActiveClassesForm()

    form.gclassid.choices = [(gClass.gclassid,gClass.gclassdict['name'])]
    isStuList = False
    if form.validate_on_submit():
        gclass = GoogleClassroom.objects.get(gclassid = form.gclassid.data)
        enrollments = GEnrollment.objects(gclassroom = gclass)

        if not form.students.data:
            stuGIdList = [('----','!Anyone'),(gclass.gteacherdict['id'],f"!Teacher: {gclass.gteacherdict['name']['familyName']}")]

            for enrollment in enrollments:
                stuName = f"{enrollment.owner.fname} {enrollment.owner.lname}"
                if enrollment.sortCohort:
                    stuName = f"{enrollment.sortCohort} {stuName}"
                stuGIdList.append((enrollment.owner.gid,stuName))
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
                    msg = f"{currUser.fname} {currUser.lname} has requested your help in {gclass.gclassdict['name']}."
                    txtOneStu(reqHelper.gid,msg)
                    msg = f""
                    txtOneStu(gclass.gteacherdict['id'],f"{currUser.fname} {currUser.lname} requested {reqHelper.fname} {reqHelper.lname}'s help in {gclass.gclassdict['name']}.")

            return redirect(url_for('classdash',gclassid=gclass.gclassid))

    return render_template('helpform.html', currUser=currUser, form=form, isStuList = isStuList)

@app.route('/help/offer/<helpid>')
def offerhelp(helpid):

    offerHelp = Help.objects.get(pk=helpid)
    currUser = current_user

    if currUser == offerHelp.requester:
        flash("You can't be the helper AND the help requester.")
        return redirect(url_for('classdash',gclassid=offerHelp.gclass.gclassid))

    if offerHelp.helper:
        flash("There is already a helper for this help.")
        return redirect(url_for('classdash',gclassid=offerHelp.gclass.gclassid))

    offerHelp.update(
        helper = currUser,
        status = "offered",
        offered = dt.utcnow()
    )

    return redirect(url_for('classdash',gclassid=offerHelp.gclass.gclassid))

@app.route('/help/recind/<helpid>')
def helprecind(helpid):
    recindHelp = Help.objects.get(pk=helpid)
    currUser = current_user

    if currUser == recindHelp.helper:
        recindHelp.update(
            helper = None,
            status = "asked",
            offered = None
        )
        flash('Offer has been recinded.')
    else:
        flash("Offer can't be recinded because you are not the Helper.")

    return redirect(url_for('classdash',gclassid=recindHelp.gclass.gclassid))


@app.route('/help/confirm/<helpid>', methods=['GET', 'POST'])
def confirmhelp(helpid):
        
    confirmHelp = Help.objects.get(pk=helpid)
    currUser = current_user
    form = SimpleForm()

    if currUser.role.lower() == "teacher" and not confirmHelp.helper:
        confirmHelp.update(
            helper = currUser
        )
        confirmHelp.reload()

    if confirmHelp.requester != currUser and currUser.role.lower() != "teacher":
        flash('You can only confirm a help that you have requested.')
        return redirect(url_for('classdash',gclassid=confirmHelp.gclass.gclassid))

    if not confirmHelp.helper:
        flash('You can only confirm a help where there is a helper.')
        return redirect(url_for('classdash',gclassid=confirmHelp.gclass.gclassid))

    if confirmHelp.status == "confirmed" or confirmHelp.status == "rejected" or confirmHelp.status == "approved":
        flash('This help is already been confirmed.')
        return redirect(url_for('classdash',gclassid=confirmHelp.gclass.gclassid))

    if currUser.role.lower() == 'student' and not form.validate_on_submit():
        return render_template('confirmform.html',form=form)
    
    confirmHelp.update(
        confirmed = dt.utcnow(),
        status = "confirmed",
        confirmdesc = form.field.data
    )
    banker = User.objects.get(oemail='stephen.wright@ousd.org')
    # give the help requester a Token for requesting a help that is now confirmed
    requester1 = Token(
        giver = banker,
        owner = confirmHelp.requester,
        help = confirmHelp,
        amt = 0
    )
    requester1.save()

    # If the help was confirmed by the requester, give them another token
    if currUser == confirmHelp.requester:
        requester2 = Token(
            giver = banker,
            owner = confirmHelp.requester,
            help = confirmHelp,
            amt = 0
        )
        requester2.save()

    # If the helper is a student, give them a token
    if confirmHelp.helper.role.lower() == "student":
        helper1 = Token(
            giver = banker,
            owner = confirmHelp.helper,
            help = confirmHelp,
            amt = 0
        )
        helper1.save()

    return redirect(url_for('classdash',gclassid=confirmHelp.gclass.gclassid))


@app.route('/help/delete/<helpid>')
def deletehelp(helpid):

    delHelp = Help.objects.get(pk=helpid)
    gclassid = delHelp.gclass.gclassid
    currUser = current_user

    if currUser.role.lower() == "teacher":
        delHelp.delete()
        flash('The requested Help is deleted.')
        return redirect(url_for('classdash',gclassid=gclassid))

    if currUser != delHelp.requester:
        flash('You are not the requester of the help so you cannot delete it.')
        return redirect(url_for('classdash',gclassid=gclassid))

    if delHelp.status == "confirmed":
        flash("You can't delete a confirmed help.")
        return redirect(url_for('classdash',gclassid=gclassid))

    delHelp.delete()
    flash('Your requested Help is deleted.')

    return redirect(url_for('classdash',gclassid=gclassid))

@app.route('/approvehelps/<gclassid>')
def approvehelps(gclassid):
    return redirect(url_for('classdash',gclassid=gclassid))

@app.route('/approvehelp/<helpid>')
def approvehelp(helpid):
    help = Help.objects.get(pk=helpid)
    help.update(status='approved')
    tokens = Token.objects(help=help)
    for token in tokens:
        if token.amt == 0:
            token.update(amt=1)
        else:
            flash("Token already awarded.")
    
    return redirect(url_for('classdash',gclassid=help.gclass.gclassid))

@app.route('/rejecthelp/<helpid>')
def rejecthelp(helpid):
    help = Help.objects.get(pk=helpid)
    help.update(
        status = 'rejected',
        note = 'Rejected for bad or missing confirmation description.'
        )
    help.reload()
    
    return redirect(url_for('classdash',gclassid=help.gclass.gclassid))

@app.route('/approveallconfirmed/<gclassid>')
def approveallconfirmed(gclassid):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    helps = Help.objects(gclass=gClassroom,status='confirmed')
    helps.update(status='approved')
    helps = Help.objects(gclass=gClassroom)

    return redirect(url_for('classdash', gclassid=gclassid))

@app.route('/tokens/award/<gclassid>', methods=["GET","POST"])
def tokensAward(gclassid):
    if session['role'].lower() !="teacher":
        flash("You can't award tokens")
        return(redirect(url_for('classdash',gclassid=gclassid)))

    currUser = current_user
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    enrollments = GEnrollment.objects(gclassroom=gClassroom)
    owners = []
    for enrollment in enrollments:
        owner = (enrollment.owner.gid, f"{enrollment.owner.fname} {enrollment.owner.lname}")
        owners.append(owner)

    owners.sort(key=lambda x:x[1])

    form = TokenForm()
    form.owner.choices = owners
    if form.validate_on_submit():
        tokenReceiver = User.objects.get(gid=form.owner.data)
        Token(
            owner = tokenReceiver,
            giver = currUser,
            note = form.note.data,
            amt = form.numTokens.data
        ).save()
        
        return(redirect(url_for('classdash',gclassid=gclassid)))

    return render_template("tokenform.html",form=form,owners=owners)

@app.route('/tokens/list')
def tokensList():
    tokens = Token.objects()
    for token in tokens:
        flash(f'{token.owner.fname} {token.owner.lname} {token.transaction}')

    return render_template('index.html')
