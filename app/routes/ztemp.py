from flask.helpers import url_for
from app import app
from flask import render_template, redirect, flash, session
from app.classes.data import CheckIn, User,Help
from mongoengine import Q
import requests
import time

# @app.route("/fixcheckins")
# def fixcheckins():
#     query = Q(workingon__exists = False) and Q(desc__exists = True)
#     checkins = CheckIn.objects(query)
#     length = len(checkins)
#     for i,checkin in enumerate(checkins):
#         checkin.update(
#             workingon = checkin.desc,
#             unset__desc = 1
#         )
#         print(f"{i}/{length}")
#     return


# @app.route('/addlatlon')
# def addlatlon():

#     query = Q(astreet__exists=True) & Q(acity__exists=True) & Q(astate__exists=True) & Q(azipcode__exists=True) & Q(lat__exists=False) & Q(lon__exists=False)

#     users = User.objects(query)
#     total = len(users)
#     for i,user in enumerate(users):

#         if user.ustreet:
#             street = user.ustreet
#         else:
#             street = user.astreet

#         if user.ucity:
#             city = user.ucity
#         else:
#             city = user.acity

#         if user.ustate:
#             state = user.ustate
#         else:
#             state = user.astate

#         if user.uzipcode:
#             zipcode = user.uzipcode
#         else:
#             zipcode = user.azipcode

#         url = f"https://nominatim.openstreetmap.org/search?street={street}&city={city}&state={state}&postalcode={zipcode}&format=json&addressdetails=1&email=stephen.wright@ousd.org"
#         r = requests.get(url)
#         try:
#             r = r.json()
#         except:
#             pass
#         else:
#             if len(r) != 0:
#                 user.lat = float(r[0]['lat'])
#                 user.lon = float(r[0]['lon'])
#                 user.save()
#                 print(f"{i}/{total}: {user.lat} {user.lon}")
#                 time.sleep(2)
#     return render_template("index.html")

# @app.route('/deleteopenhelps')
# def deleteopenhelps():
#     statusList = ['asked','offered']
#     openHelps = Help.objects(status__in = statusList)
#     print(len(openHelps))
#     openHelps.delete()
#     openHelps = Help.objects(status__in = statusList)
#     print(len(openHelps))

#     return render_template('index.html')


# @app.route('/updategclasses')
# def updategclasses():
#     users = User.objects(gclasses__exists = True )
#     for j,user in enumerate(users):
#         print(f"{j}/{len(users)} {user.fname} {user.lname}")
#         changed = False
#         for i,otclass in enumerate(user.gclasses):
#             if otclass.gclassroom:
#                 print(f"{i}/{len(user.gclasses)} {otclass.gclassroom.gclassdict['name']}")
#                 if otclass.classname:
#                     tempName = otclass.classname
#                 else:
#                     tempName = otclass.gclassroom.gclassdict['name']
#                 #print(f"tempName: {tempName}")
#                 if otclass.status and otclass.status.lower() == "active":
#                     tempStatus = otclass.status
#                 else:
#                     tempStatus = "Inactive"
#                 #print(f"tempStatus: {tempStatus}")
#                 if not otclass.classname or not otclass.status:
#                     user.gclasses.filter(gclassid = otclass.gclassid).update(
#                         classname = tempName, 
#                         status = tempStatus
#                     )
#                     changed = True
#         if changed:
#             user.save()
#             print('saved')
#         else:
#             print('not saved')
#     return render_template('index.html')