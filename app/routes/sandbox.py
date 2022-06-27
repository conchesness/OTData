from app import app
from flask import render_template, redirect, session, flash, url_for
import requests
import datetime
from zoneinfo import ZoneInfo

@app.route('/sandbox')
def sandbox():
    return render_template('sandbox.html')

@app.route('/weather/<city>/<state>/<country>')
def weather(city,state,country):
    w = requests.get(f'https://api.openweathermap.org/data/2.5/weather?q={city},{state},{country}&appid=c9dffd9e0a9b5fcbd79580782d2cf394&units=imperial')
    w=w.json()

    # When these datetimes are uploaded to the server they will be changed to utc so 
    # if you convert them on the template to local time (via the moment.js library for example)
    # they will show up incorrectly on the local server. You can use an if statement on the tmeplate to 
    # check for the host first and then choose to use Moment when it is on the server and strftime when it is local. 
    pacific = ZoneInfo('US/Pacific')

    sunrise = datetime.datetime.fromtimestamp(w['sys']['sunrise'])
    sunrise = sunrise.replace(pacific)

    sunset = datetime.datetime.fromtimestamp(w['sys']['sunset'])
    sunset = sunset.replace(pacific)

    f = requests.get(f"https://api.openweathermap.org/data/2.5/onecall?lat={w['coord']['lat']}&lon={w['coord']['lon']}&appid=c9dffd9e0a9b5fcbd79580782d2cf394&units=imperial&exclude=current,minutely")
    f = f.json()
    for hour in f['hourly']:
        timeTemp = datetime.datetime.fromtimestamp(hour['dt'])
        hour['dt'] = timeTemp.replace(pacific)

    return render_template('sandbox.html',w=w,f=f,sunrise=sunrise,sunset=sunset)