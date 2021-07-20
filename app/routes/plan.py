from contextlib import redirect_stderr
from app import app
import os
from flask import render_template, redirect, url_for, flash, session, Markup, request
from app.classes.data import Plan, User, PlanSettings, PlanCheckin
from app.classes.forms import PlanThemeForm, PlanIdealOutcomeForm, PlanSettingsForm, PlanCheckinForm
from bson.objectid import ObjectId
import mongoengine.errors
import datetime as d
import time

@app.route('/plansettings', methods=["GET","POST"])
def plansettings():
    if session['isadmin'] != True:
        flash('You must be an administrator to access Success Plan Settings.')
        return redirect(url_for('index'))

    form = PlanSettingsForm()

    settings = PlanSettings.objects.first()
    
    if form.validate_on_submit():
        settings.update(
            timeframe = form.timeframe.data,
            yearbegin = form.yearbegin.data,
            summerbegin = form.summerbegin.data,
            seasonwinterbegin = form.seasonwinterbegin.data,
            seasonspringbegin = form.seasonspringbegin.data,
            semestertwobegin = form.semestertwobegin.data
        )
        settings.reload()

    try: 
        settings.id
    except:
        PlanSettings().save()
        settings = PlanSettings.objects.first()
    else:
        form.timeframe.data = settings.timeframe
        form.yearbegin.data = settings.yearbegin
        form.summerbegin.data = settings.summerbegin
        form.seasonwinterbegin.data = settings.seasonwinterbegin
        form.seasonspringbegin.data = settings.seasonspringbegin
        form.semestertwobegin.data = settings.semestertwobegin

    return render_template("plans/plansettings.html", form=form, settings=settings)

@app.route('/plan')
@app.route('/plan/<gid>')
def plan(gid=None):
    if not gid:
        gid=session['gid']
        
    student=User.objects.get(gid=gid)

    try:
        plan = Plan.objects.get(student=student)
    except mongoengine.errors.DoesNotExist:
        flash(Markup(f"{student.fname} {student.lname} Doesn't have a plan. Make a <a href='/plannew/{gid}'>new plan</a>"))
        return redirect(url_for('profile', aeriesid=student.aeriesid))
    except Exception as error:
        flash(f"An unkown error occured: {error}")
        return redirect(url_for('profile', aeriesid=student.aeriesid))

    checkins = PlanCheckin.objects(plan = plan).order_by("-createdate")
    if checkins:
        for checkin in checkins:
            lastCheckin = checkin
            break
    else:
        lastCheckin = None

    settings=PlanSettings.objects.first()
    status = 0
    themes = plan.themes.filter(old = 0)

    numActiveThemes = len(themes)

    if len(themes) > 0:
        status += 1
    
    if themes and len(themes[0].idealoutcomes) > 2:
        status += 1

    return render_template('plans/plan.html', plan=plan,settings=settings,status=status,numActiveThemes=numActiveThemes, checkins=checkins, lastCheckin = lastCheckin)

# TODO will need pagination eventually
@app.route('/plans')
def allplans():
    plans = Plan.objects()
    
    return render_template('plans/plans.html', plans=plans)

@app.route('/plannew', methods=['GET', 'POST'])
@app.route('/plannew/<gid>', methods=['GET', 'POST'])
def plannew(gid=None):

    if not gid:
        gid = session['gid']

    if session['gid'] != gid and not session['isadmin']:
        flash("You can only create Plans for yourself.")
        return redirect(url_for("profile"))

    student = User.objects.get(gid = gid)

    try: 
        plan = Plan.objects.get(student=student)
        flash('Student already has a plan.')
        return redirect(url_for('plan'),gid=gid)

    except:
        newPlan = Plan(
            student=student
        )
        newPlan.save()

    return redirect(url_for('plan',gid=gid))

def checkPlanEditPriv(gid):
    if gid != session['gid'] and not session['isadmin']:
        flash("You can only create, edit or delete Plans for yourself.")
        return False
    else:
        return True

@app.route('/planthemenew/<planid>', methods=['GET', 'POST'])
def planthemenew(planid):

    editPlan = Plan.objects.get(pk=planid)

    activeThemes = editPlan.themes.filter(old=False)
    if len(activeThemes) > 1:
        flash('You already have at least one active theme. Edit that theme and set it to "old" before you try to create a new theme.')
        return redirect(url_for("plan",gid=editPlan.student.gid))

    canEdit = checkPlanEditPriv(editPlan.student.gid)
    if not canEdit:
        return redirect(url_for("profile"))

    settings = PlanSettings.objects.first()
    form = PlanThemeForm()
    form.timeframe.choices=[settings.timeframe]

    if form.validate_on_submit():
        editPlan.themes.create(
            oid = ObjectId(),
            name = form.name.data,
            timeframe = form.timeframe.data,
            description = form.description.data,
            old = False
        )
        editPlan.save()
        return redirect(url_for('plan',gid=editPlan.student.gid))

    return render_template('plans/planedit.html', form=form, plan=editPlan, planThemeForm=True,settings=settings)

@app.route('/planthemeedit/<planid>/<planthemeid>', methods=['GET', 'POST'])
def planthemeedit(planid,planthemeid):
    editPlan = Plan.objects.get(pk=planid)

    canEdit = checkPlanEditPriv(editPlan.student.gid)
    if not canEdit:
        return redirect(request.url)

    try:
        editTheme = editPlan.themes.get(oid=planthemeid)
    except:
        flash(f"This user does not have a theme.")
        return redirect(url_for('plan',gid=editPlan.student.gid))

    settings = PlanSettings.objects.first()
    form = PlanThemeForm()
    form.timeframe.choices = [settings.timeframe]

    if form.validate_on_submit():
        editPlan.themes.filter(oid=planthemeid).update(
            oid = ObjectId(),
            name = form.name.data,
            timeframe = form.timeframe.data,
            description = form.description.data,
            old = form.old.data
        )
        editPlan.save()
        return redirect(url_for('plan',gid=editPlan.student.gid))

    form.name.data = editTheme.name
    form.timeframe.data = editTheme.timeframe
    form.description.data = editTheme.description
    form.old.data = editTheme.old

    return render_template('plans/planedit.html', form=form, plan=editPlan, planThemeForm=True, theme=editTheme, settings=settings)

@app.route('/planthemedelete/<planid>/<planthemeid>')
def planthemedelete(planid,planthemeid):
    editPlan = Plan.objects.get(pk=planid)
    theme = editPlan.themes.get(oid=planthemeid)

    if len(theme.idealoutcomes) > 0:
        flash("You can't delete a Theme while it has Ideal Outcomes. Delete the Ideal Outcomes first.")
        return redirect(url_for('plan',gid=editPlan.student.gid))

    canEdit = checkPlanEditPriv(editPlan.student.gid)
    if not canEdit:
        flash("You don't have necessary permisions to delete this Theme.")
        return redirect(url_for('plan',gid=editPlan.student.gid))

    editPlan.themes.filter(oid=planthemeid).delete()
    editPlan.save()

    return redirect(url_for("plan",planid=planid))

@app.route('/planidealoutcomenew/<planid>/<themeid>', methods=['GET', 'POST'])
def planidealoutcomenew(planid,themeid):
    editPlan = Plan.objects.get(pk=planid)

    canEdit = checkPlanEditPriv(editPlan.student.gid)
    if not canEdit:
        return redirect(url_for("profile"))

    editTheme = editPlan.themes.get(oid=themeid)
    settings = PlanSettings.objects.first()
    form = PlanIdealOutcomeForm()

    if form.validate_on_submit():
        editTheme.idealoutcomes.create(
            oid = ObjectId(),
            name = form.name.data,
            description = form.description.data,
            example = form.example.data
        )
        editPlan.save()
        return redirect(url_for('plan',gid=editPlan.student.gid))

    return render_template('plans/planedit.html', form=form, plan=editPlan, planIdealOutcomeForm=True, theme=editTheme, settings=settings)

@app.route('/planidealoutcomeedit/<planid>/<themeid>/<idealoutcomeid>', methods=['GET', 'POST'])
def planidealoucomeedit(planid,themeid, idealoutcomeid):
    editPlan = Plan.objects.get(pk=planid)

    canEdit = checkPlanEditPriv(editPlan.student.gid)
    if not canEdit:
        return redirect(url_for("profile"))

    editTheme = editPlan.themes.get(oid=themeid)
    editIdealOutcome = editTheme.idealoutcomes.get(oid=idealoutcomeid)
    settings=PlanSettings.objects.first()
    form = PlanIdealOutcomeForm()

    if form.validate_on_submit():
        editTheme.idealoutcomes.filter(oid=idealoutcomeid).update(
            name = form.name.data,
            description = form.description.data,
            example = form.example.data
        )
        editPlan.save()
        return redirect(url_for('plan',gid=editPlan.student.gid))
    
    form.name.data = editIdealOutcome.name
    form.description.data = editIdealOutcome.description
    form.example.data = editIdealOutcome.example

    return render_template('plans/planedit.html', form=form, plan=editPlan, planIdealOutcomeForm=True, theme=editTheme, settings=settings)

@app.route('/planidealoutcomedelete/<planid>/<themeid>/<idealoutcomeid>')
def planidealoutcomedelete(planid,themeid, idealoutcomeid):
    editPlan = Plan.objects.get(pk=planid)

    canEdit = checkPlanEditPriv(editPlan.student.gid)
    if not canEdit:
        return redirect(url_for("profile"))

    editTheme = editPlan.themes.get(oid=themeid)
    editIdealOutcome = editTheme.idealoutcomes.get(oid=idealoutcomeid)
    idealOutcomeName=editIdealOutcome.name
    try:
        editTheme.idealoutcomes.filter(oid=idealoutcomeid).delete()
        success=True
    except Exception as error:
        flash(f"There was an error when trying to delete the Ideal Outcome: {error}")
    editPlan.save()
    flash(f"Ideal Outcome named '{idealOutcomeName}' in Theme '{editTheme.name}' was successfully deleted.")
    return redirect(url_for('plan',gid=editPlan.student.gid))

@app.route('/plancheckin/<gid>/<themeoid>/<iooid>', methods=['GET', 'POST'])
@app.route('/plancheckin/<gid>/<themeoid>', methods=['GET', 'POST'])
def plancheckin(gid,themeoid,iooid=None):

    planUser=User.objects.get(gid=gid)
    
    try:
        userPlan=Plan.objects.get(student=planUser)
    except:
        flash("You have to have a plan before you can checkin. Make <a href='/plannew/{gid}'>new plan</a> ")
        return redirect(url_for('profile'))

    checkins = PlanCheckin.objects(plan = userPlan).order_by("-createdate")
    lastCheckin = None
    for checkin in checkins:
        lastCheckin = checkin
        break  

    todayCheckins = PlanCheckin.objects(plan = userPlan, createdate__gt = d.datetime.utcnow().date())

    if todayCheckins:
        flash("You already have a checkin today. Either edit that one or delete it and start again.")
        return redirect(url_for("plan",gid=gid))

    try:
        userTheme = userPlan.themes.get(oid=themeoid)
    except:
        flash("You have to have a theme and at least three Ideal Outcomes before you can checkin.")
        return redirect(url_for('plan',gid=gid))

    form=PlanCheckinForm()

    choices = []
    for io in userTheme.idealoutcomes:
        choices.append((io.name,io.name)) 
    form.todayfocus.choices = choices

    if iooid:
        userIdealOutcome = userTheme.idealoutcomes.get(oid=iooid)
        form.todayfocus.data = userIdealOutcome.name
    else:
        userIdealOutcome = None

    if form.validate_on_submit():

        if lastCheckin and not form.yesterdayrating.data:
            flash("You must rate your last checkin.")
            return redirect(url_for('plancheckin', gid=gid, themeoid=themeoid, iooid=iooid))
        
        if form.yesterdayrating.data == '0':
            flash("You need to choose a 1 - 4 rating of your last checkin.")
            return redirect(url_for('plancheckin', gid=gid, themeoid=themeoid, iooid=iooid))

        if lastCheckin:
            newPlanCheckin = PlanCheckin(
                createdate = d.datetime.utcnow(),
                plan = userPlan,
                todayfocus = form.todayfocus.data,
                yesterdayrating = form.yesterdayrating.data,
                yesterdaynarrative = form.yesterdaynarrative.data,
                todaynarrative = form.todaynarrative.data,
                previousreference = lastCheckin
            )
        else:
            newPlanCheckin = PlanCheckin(
                createdate = d.datetime.utcnow(),
                plan = userPlan,
                todayfocus = form.todayfocus.data,
                yesterdayrating = form.yesterdayrating.data,
                yesterdaynarrative = form.yesterdaynarrative.data,
                todaynarrative = form.todaynarrative.data
            )

        newPlanCheckin.save()
        return redirect(url_for("plan",gid=gid))

    return render_template('plans/plancheckin.html', form=form, theme=userTheme, planUser=planUser,lastcheckin=lastCheckin)

@app.route("/plancheckindelete/<plancheckinid>/<gid>")
def plancheckindelete(plancheckinid,gid=None):
    if not gid:
        gid = session['gid']
    plancheckin = PlanCheckin.objects.get(id = plancheckinid)
    if plancheckin.createdate.date() < d.datetime.utcnow().date() and not session['isadmin']:
        flash('You can only delete checkins from today')
        return redirect(url_for('plan',gid=gid))
    plancheckin.delete()
    return redirect(url_for('plan',gid=gid))

@app.route("/plancheckinedit/<plancheckinid>/<gid>", methods=['GET', 'POST'])
def plancheckinedit(plancheckinid,gid=None):
    if not gid:
        gid = session['gid']

    plancheckin = PlanCheckin.objects.get(id = plancheckinid)
    if plancheckin.createdate.date() < d.datetime.utcnow().date() and not session['isadmin']:
        flash('You can only edit checkins from today.')
        return redirect(url_for('plan',gid=gid))

    planUser = User.objects.get(gid=gid)
    userPlan = Plan.objects.get(student=planUser)
    userTheme = userPlan.themes.get(old=False)
    
    if plancheckin.previousreference:
        lastCheckin = plancheckin.previousreference
    else:
        lastCheckin = None

    form=PlanCheckinForm()
    choices = []
    for io in userTheme.idealoutcomes:
        choices.append((io.name,io.name)) 
    form.todayfocus.choices = choices

    if form.validate_on_submit():

        if lastCheckin and not form.yesterdayrating.data:
            flash("You must rate your last checkin.")
            return render_template('plans/plancheckin.html', form=form, theme=userTheme, planUser=planUser,lastcheckin=lastCheckin)

        if form.yesterdayrating.data == '0':
            flash("You need to choose a 1 - 4 rating of your last checkin.")
            return render_template('plans/plancheckin.html', form=form, theme=userTheme, planUser=planUser,lastcheckin=lastCheckin)

        plancheckin.update(
            todayfocus = form.todayfocus.data,
            yesterdayrating = form.yesterdayrating.data,
            yesterdaynarrative = form.yesterdaynarrative.data,
            todaynarrative = form.todaynarrative.data  
        )      

        return redirect(url_for('plan',gid=gid))

    form.todayfocus.data = plancheckin.todayfocus
    form.yesterdayrating.data = str(plancheckin.yesterdayrating)
    form.yesterdaynarrative.data = plancheckin.yesterdaynarrative
    form.todaynarrative.data = plancheckin.todaynarrative

    return render_template('plans/plancheckin.html', form=form, theme=userTheme, planUser=planUser,lastcheckin=lastCheckin)

