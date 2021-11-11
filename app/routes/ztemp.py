from flask.helpers import url_for
from app import app
from flask import render_template, redirect, flash, session
from app.classes.data import User,Help
from mongoengine import Q

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
#     #users = User.objects(id = session['currUserId'])
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