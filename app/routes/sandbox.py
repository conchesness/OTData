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
    w = requests.get(f'https://api.openweathermap.org/data/2.5/weather?q={city},{state},{country}&appid=c9dffd9e0a9b5fcbd79580782d2cf394&units=imperial')
    w=w.json()
    print(w)

    pacific = timezone('US/Pacific')

    sunrise = datetime.datetime.fromtimestamp(w['sys']['sunrise'])
    print(sunrise)
    sunrise = pacific.localize(sunrise)
    print(sunrise)

    sunset = datetime.datetime.fromtimestamp(w['sys']['sunset'])
    sunset = pacific.localize(sunset)

    f = requests.get(f"https://api.openweathermap.org/data/2.5/onecall?lat={w['coord']['lat']}&lon={w['coord']['lon']}&appid=c9dffd9e0a9b5fcbd79580782d2cf394&units=imperial&exclude=current,minutely")
    f = f.json()
    for hour in f['hourly']:
        timeTemp = datetime.datetime.fromtimestamp(hour['dt'])
        hour['dt'] = pacific.localize(timeTemp)

    return render_template('sandbox.html',w=w,f=f,sunrise=sunrise,sunset=sunset)