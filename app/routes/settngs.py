from app import app
from flask import render_template, redirect, session, flash, url_for, request, Markup
from app.classes.data import Schedule
from app.classes.forms import  ScheduleForm

@app.route('/schedules')
def schedules():
    schedules = Schedule.objects()

    return render_template('schedules.html',schedules = schedules)

@app.routes('/newSchedule')
def newSchedule():
    form = ScheduleForm()

    if form.validate_on_submit():
        Schedule(
            active = form.active.data,
            name = form.name.data
        )
    pass