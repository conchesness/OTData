from app import app
from flask import render_template, redirect, session, flash, url_for
import requests
import datetime
from pytz import timezone
import pytz

# from app.classes.data import GoogleClassroom, User, Help, Token

@app.route('/sandbox')
def sandbox():
    return render_template('sandbox.html')

@app.route('/weather/<city>/<state>/<country>')
def weather(city,state,country):
    r = requests.get(f'https://api.openweathermap.org/data/2.5/weather?q={city},{state},{country}&appid=c9dffd9e0a9b5fcbd79580782d2cf394&units=imperial')

    pacific = timezone('US/Pacific')

    sunrise = datetime.datetime.fromtimestamp(r.json()['sys']['sunrise'])
    sunrise = pacific.localize(sunrise)

    sunset = datetime.datetime.fromtimestamp(r.json()['sys']['sunset'])
    sunset = pacific.localize(sunset)

    return render_template('sandbox.html',r=r,sunrise=sunrise,sunset=sunset)