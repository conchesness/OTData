from flask.helpers import url_for
from app import app
from flask import render_template, redirect, flash
from app.classes.data import User, Section, Config, Section, Course, GoogleClassroom, Plan
import pandas as pd
import time
from mongoengine.errors import NotUniqueError
from bson import ObjectId

@app.route('/unsetplans')
def unsetplans():
    plans = Plan.objects()
    for plan in plans:
        try:
            plan.goals
        except:
            pass
        else:
            plan.update(
                unset__goals=1
            )
        try:
            plan.statement
        except:
            pass
        else:
            plan.update(
                unset__statement=1
            )
    pass

@app.route('/fixnames')
def fixnames():
    users = User.objects()
    count = len(users)
    for i,editUser in enumerate(users):
        if editUser.ufname:
            fname = editUser.ufname
        else:
            fname = editUser.afname

        if editUser.ulname:
            lname = editUser.ulname
        else:
            lname = editUser.alname

        if fname != editUser.fname or lname != editUser.lname:
            editUser.update(
                fname = fname,
                lname = lname
            )
            print(f"{i}:{count} Stored new name for {fname} {lname}")
    return redirect(url_for('index'))

# @app.route('/importsections')
# def importsections():
#     df_sections = pd.read_csv('csv/sections.csv', encoding = "ISO-8859-1")
#     df_sections.fillna('', inplace=True)
#     sections = df_sections.to_dict(orient='records')

#     badcnums=[]
#     length=len(sections)
#     for i,section in enumerate(sections):
#         try:
#             course=Course.objects.get(aeriesnum=section['cnum'])
#         except:
#             badcnums.append((section['cnum'],section['cname']))
#             print(section['cname'])
#         else:
#             try:
#                 teacher=User.objects.get(tnum=section['tnum'])
#             except:
#                 teacher=None
#             pers=str(section['pers'])
#             newSection=Section(
#                 course=course,
#                 teacher=teacher
#             )
#             for per in pers:
#                 newSection.pers.append(per)
#             try:
#                 newSection.save()
#             except NotUniqueError:
#                 pass
#         print(f"{i}/{length}")

#     badcnums=set(badcnums)
#     print(badcnums)

#     pass



@app.route('/unsetsectionsoncourse')
def unsetsectionsoncourse():
    courses=Course.objects()
    courses.update(
            unset__sections=1
        )
    return redirect(url_for('courses'))


@app.route('/coursestocsv')
def coursestocsv():
    courses=Course.objects()
    courses_json = courses.to_json()
    courses_df = pd.read_json(courses_json)
    del courses_df['_id','sections']
    courses_csv = courses_df.to_csv()
    print(courses_csv)
    return redirect(url_for('index'))


## Scripts for getting Aeries ID's ###
##This script takes a csv of students and edits aeries records or creates a new aeries record.
##This script just replaces all the data with new data on an edit.
@app.route('/aeriesstudentimport')
def aeriesstudentimport():
    # TODO: need to add gpa to csv and import script


    # This reads a csv file in to a dataframe
    df_aeries = pd.read_csv('csv/aeries.csv', encoding = "ISO-8859-1")
    df_aeries.fillna('', inplace=True)

    #  This turns that dataframe in to a python dictionary
    students = df_aeries.to_dict(orient='records')
    length = len(students)
    # This iteratates through the students dict
    for index, student in enumerate(students):
        # Using the aeriesId as the unique ID, if the Aeries record exists, update all values
        try:
            editAeries = User.objects.get(aeriesid = int(student['aeriesid']))
        except:
            editAeries = False

        if editAeries:
            editAeries.update(
                afname = student['afname'],
                alname = student['alname'],
                aphone = student['aphone'],
                azipcode = student['zipcode'],
                astreet = student['street'],
                acity = student['city'],
                astate = student['state'],
                aadults = student['aadults'],
                aadultemail = student['adultemail'],
                aadult1phone = student['adult1phone'],
                aadult2phone = student['adult2phone'],
                agender = student['gender'],
                grade = student['grade'],
                aethnicity = student['ethnicity'],
                cohort = student['cohort'],
                langflu = student['langflu'],
                sped = student['sped'],
                gpa = student['gpa'],
                role = 'student'
            )
            print(f"{index}:{length} {editAeries.otemail} edited")
        else:
            # If the Aeries record does not exist, create it using the values in the dictionary
            newAeries = User(
                aeriesid = student['aeriesid'],
                otemail = student['otemail'],
                afname = student['afname'],
                alname = student['alname'],
                aphone = student['aphone'],
                azipcode = student['zipcode'],
                astreet = student['street'],
                acity = student['city'],
                astate = student['state'],
                aadults = student['aadults'],
                aadultemail = student['adultemail'],
                aadult1phone = student['adult1phone'],
                aadult2phone = student['adult2phone'],
                agender = student['gender'],
                grade = student['grade'],
                aethnicity = student['ethnicity'],
                cohort = student['cohort'],
                langflu = student['langflu'],
                sped = student['sped'],
                gpa = student['gpa'],
                role = 'student'
            ).save()
            print(f'{index}:{length} {newAeries.otemail} created')

    return render_template('index.html')


@app.route('/addallaeriesteachers')
def addallaeriesTeachers():
    settings = Config.objects.first()
    if settings.devenv == False:
        flash("You can only run scripts in a local environment.")
        return redirect('/')

    # This reads a csv file in to a dataframe
    df_aeriesteachers = pd.read_csv('csv/aeriesteachers.csv')
    df_aeriesteachers.fillna('', inplace=True)

    #  This turns that dataframe in to a python dictionary
    aeriesteachers = df_aeriesteachers.to_dict(orient='records')
    l = len(aeriesteachers)

    for index, teacher in enumerate(aeriesteachers):

        try:
            otdatateacher = User.objects.get(otemail = teacher['email'].strip())
            editTeacher = True
        except:
            editTeacher = False

        if not teacher['teachernum']:
            teacher['teachernum'] = 0

        if editTeacher:
            otdatateacher.update(
                taeriesname = teacher['aeriesname'].strip(),
                tnum = teacher['teachernum'],
                afname = teacher['fname'].strip(),
                alname = teacher['lname'].strip(),
                troom = teacher['room'].strip(),
                trmphone = teacher['rmphone'].strip(),
                tdept = teacher['dept'].strip(),
                role = teacher['title'].strip()
            )
            otdatateacher.reload()
        else:
            otdatateacher = User(
                taeriesname = teacher['aeriesname'],
                tnum = teacher['teachernum'],
                afname = teacher['fname'],
                alname = teacher['lname'],
                otemail = teacher['email'],
                troom = teacher['room'],
                trmphone = teacher['rmphone'],
                tdept = teacher['dept'],
                role = teacher['title']
            )
            otdatateacher.save()

        print(f"{index}/{l}: {otdatateacher.taeriesname}")
        
    return redirect('/')

@app.route('/addsections')
def addsections():

    settings = Config.objects.first()
    if settings.devenv == False:
        flash("You can only run scripts in a local environment.")
        return redirect('/')

    # This reads a csv file in to a dataframe
    df_aeriessections = pd.read_csv('csv/aeriessections.csv')
    df_aeriessections.fillna('', inplace=True)

    #  This turns that dataframe in to a python dictionary
    aeriessections = df_aeriessections.to_dict(orient='records')
    l = len(aeriessections)
    for i, section in enumerate(aeriessections):
        try:
            teacher = User.objects.get(tnum = section['tnum'])
        except:
            teacher = None

        newSection = Section(
            teacher = teacher,
            coursename = section['course'].strip(),
            coursenum = section['coursenum'].strip(),
            per = section['per'],
            num = section['sectionnum'],
            room = section['room'].strip()
        )
        newSection.save()

        if teacher:
            teacher.update(add_to_set__sections = newSection)

        print(f'{i}/{l}: New section number {newSection.num}: {newSection.per} {newSection.coursename} ')
    return render_template('index.html')

@app.route('/linksectionsandstudents')
def linksectionsandstudents():

    settings = Config.objects.first()
    if settings.devenv == False:
        flash("You can only run scripts in a local environment.")
        return redirect('/')

    # This reads a csv file in to a dataframe
    df_aeriesenrollments = pd.read_csv('csv/aeriesenrollments.csv')
    df_aeriesenrollments.fillna('', inplace=True)

    #  This turns that dataframe in to a python dictionary
    aeriesenrollments = df_aeriesenrollments.to_dict(orient='records')
    l = len(aeriesenrollments)

    for i, enrollment in enumerate(aeriesenrollments):
        try:
            student = User.objects.get(aeriesid = enrollment['aeriesid'])
            studentexists = True
        except:
            studentexists = False

        try:
            section = Section.objects.get(num = int(enrollment['sectionnum']))
            sectionexists = True
        except:
            sectionexists = False

        if studentexists and sectionexists:
            # newEnrollment = Enrollment(section = section)
            # student.enrollments.append(newEnrollment)
            # student.save()
            student.update(add_to_set__sections = section)
            section.update(add_to_set__students = student)
            if i % 100 == 0:
                print(f"{i}/{l}: {student.afname} {student.afname} is linked to {section.num}: {section.coursename}")
    return redirect('/')
        
    

## This script adds all the classes a student is enrolled in to the classes list on their
## Aeries record
## TODO - delete the existing classes when it's a new year update

## TODO this doesn't work with DB schema changes
# @app.route('/addaeriescourses')
# def addaeriescourses():
#     start_time = time.time()

#     # This reads a csv file in to a dataframe
#     df_aeriesenrollments = pd.read_csv('aeriesenrollments.csv')
#     df_aeriesenrollments.fillna('', inplace=True)

#     #  This turns that dataframe in to a python dictionary
#     aeriesenrollments = df_aeriesenrollments.to_dict(orient='records')
#     total = len(aeriesenrollments)

#     for index, enrollment in enumerate(aeriesenrollments):
#         editAeries = Aeires.objects.get(aeriesId=enrollment['aeriesId'])
#         addSection = Aeriessection.objects.get(sectionnum=enrollment['sectionnum'])
#         editAeries.update(add_to_set__aeriesclasses = addSection)
#         if index % 10 == 0:
#             print(f'{index} of {total} in {(time.time() - start_time)/60} mins')

#     flash(f"total mins was {(time.time() - start_time)/60}")
    
#     return render_template('index.html')


# @app.route('/addusertoaeriesteacher')
# def addusertoaeriesteacher():
#     aeriesTeachers = Teacher.objects()
#     for teacher in aeriesTeachers:
#         try:
#             teacherUser = User.objects.get(email = teacher.email)
#             print(f"{teacherUser.gfname} is a User")
#             teacher.reload()
#             print("reload Teacher Record")
#             teacher.update(
#                 user = teacherUser
#             )
#             print(f"{teacher.aeriesname} User is saved on Teacher record")
#             print()
#         except:
#             print(f"{teacher.aeriesname} is not a User")
#             print()

#     return redirect('/')

# This script connect the sections table to the teachers table
# @app.route('/addsectionstoteacher')
# def addsectiontoteacher():
#     allsects = Aeriessection.objects()
#     l=len(allsects)
#     for i,sect in enumerate(allsects):
#         try:
#             # teacher = Teacher.objects.get(teachernum=sect.teachernum)
#             teacher.update(add_to_set__sections = sect)
#             sect.update(teacherref = teacher)
#             print(f"{i}/{l}: {sect.sectionnum} {sect.course} added to {teacher.fname} {teacher.lname} and vide versa ")
#         except:
#             flash(f"Couldn't find teachernum: {sect.teachernum}")
#     return redirect('/')

# This script finds the missing teachers that are in sections but not in teachers
# @app.route('/findmissingteachers')
# def findmissingteachers():
#     # sections = Aeriessection.objects()
#     l=len(sections)
#     for i,section in enumerate(sections):
#         try:
#             teacher = Teacher.objects.get(teachernum=section.teachernum)
#         except:
#             newTeacher = Teacher(
#                 teachernum = section.teachernum,
#                 aeriesname = section.teacher
#             )
#             newTeacher.save()
#             print(f"created {newTeacher.teachernum} {newTeacher.aeriesname}")
#     return redirect('/')

@app.route('/increasegradebyone')
def increasegradebyone():
    students = User.objects(role__iexact = 'student')
    totalstudents = len(students)
    for i, student in enumerate(students):
        student.update(
            grade = student.grade + 1
        )
        print(f"{i}:{totalstudents}")
    flash("All Student grades have been increased by 1.")
        
    return redirect('/')

@app.route('/erasecs')
def erasecs():
    csstudents = User.objects(cohort__icontains = "computer")
    total = len(csstudents)
    for i,stu in enumerate(csstudents):
        stu.update(
            cohort = ""
        )
        print(f"{i}:{total}")
    return redirect('/')

@app.route('/addcsacademy')
def addcsacademy():
    start_time = time.time()

    # This reads a csv file in to a dataframe
    df_cs = pd.read_csv('csv/allcsids.csv')
    df_cs.fillna('', inplace=True)

    #  This turns that dataframe in to a python dictionary
    cs = df_cs.to_dict(orient='records')
    total = len(cs)

    for index, stu in enumerate(cs):
        try:
            student = User.objects.get(aeriesid = stu['id'])
        except:
            student = None
            print(stu['id'])

        if student and not student.cohort == 'Oakland Tech - Computer Academy':
            student.update(
                cohort = 'Oakland Tech - Computer Academy'
            )
            print(f'{index} of {total} in {(time.time() - start_time)/60} mins')

    flash(f"total mins was {(time.time() - start_time)/60}")
    
    return render_template('index.html')

@app.route('/getcohorts')
def getcohorts():
    allstudents = User.objects().order_by('cohort')
    temp = ''
    cohorts = []

    for i,stu in enumerate(allstudents):
        if stu.cohort and not temp == stu.cohort:
            cohorts.append(stu.cohort)
            temp = stu.cohort
        else:
            temp = stu.cohort
    flash(cohorts)
    return render_template('index.html')

# Delete classnames that are exactly "~"
@app.route('/deleteoldclassnames')
def deleteoldclassnames():
    users = User.objects()
    numusers = len(users)
    for i,editUser in enumerate(users):
        if len(editUser.gclasses) > 0:
            for gclass in editUser.gclasses:
                try:
                    if gclass.classname == "~":
                        delclassname = True
                    else:
                        delclassname = False
                except:
                    delclassname = False

                if delclassname:
                    print(f"{i}:{numusers}: {editUser.id} {editUser.afname}")
                    editUser.gclasses.filter(gclassid=gclass.gclassid).update(
                        classname = None
                    )
                    editUser.gclasses.filter(gclassid=gclass.gclassid).save()
    return render_template('index.html')


# Empty some depricated fields
@app.route('/deletegclassdepricated')
def deletegclassdepricated():
    users = User.objects()
    numusers = len(users)
    for i,editUser in enumerate(users):
        if len(editUser.gclasses) > 0:
            
            for gclass in editUser.gclasses:
                try:
                    td = len(gclass.gteacher)
                except:
                    td = 0
                try:
                    cd = len(gclass.gclassdict)
                except:
                    cd = 0
                if td > 0 or cd > 0:
                    print(f"{i}:{numusers}: {editUser.id} {editUser.afname}")
                    editUser.gclasses.filter(gclassid=gclass.gclassid).update(
                        gclassdict = None,
                        gteacher = None
                    )
                    editUser.gclasses.filter(gclassid=gclass.gclassid).save()
    return render_template('index.html')

# updates cohort fields for ALL students (no specific querying for just new students)
@app.route('/cleancohortdata')
def cleancohortdata():
    keywords_to_cohorts = {
        'janus' : 'Janus House', 'neptune' : 'Neptune House', 'sol' : 'Sol House', 'health' : 'Health Academy',
        'computer' : 'Computer Academy', 'engineering' : 'Engineering Academy', 'fashion' : 'Fashion, Art, and Design Academy',
        'race' : 'Race, Policy, and Law Academy', '-----':'No Academy'
    }

    
    blanks = User.objects(cohort = '')
    blanks.update(cohort = 'No Academy', multi = True)
    
    #for student in blanks:
    #    student.update(cohort = 'No Academy')

    for key in keywords_to_cohorts:
        group = User.objects(cohort__icontains = key)
        group.update(cohort = keywords_to_cohorts[key], multi = True)
        #for student in group:
        #    student.update(cohort = keywords_to_cohorts[key])
    
    # SPED-SDC kids aren't in a cohort, or not in a cohort!
    SDC_group = User.objects(sped = 'SDC (Special Day Class)', cohort = 'No Academy')
    SDC_group.update(cohort = 'No Academy - SDC', multi = True)

    return render_template('index.html')

@app.route('/unsetinterventionsfield')
def unsetinterventionsfield():
    users = User.objects()
    try:
        users.update(
            unset__interventions = 1
        )
    except Exception as error:
        print(f"unset Interventions {error}")
    
    flash('The Inteventions fields have been removed from all User records. Now delete them from the User data document.')
    return render_template('index.html')


### Notes on how to create a sandbox // requires mongodb tools on local machine
# mongodump --uri mongodb+srv://admin:bulldogz@cluster0-8m0v1.gcp.mongodb.net/otdata
# change the folder name in the dump directory to otdatasb
# C:\Users\steve\OneDrive\Documents\Code\OTData\dump
# drop the otdatasb database in Mongodb.com
# mongorestore --uri mongodb+srv://admin:bulldogz@cluster0-8m0v1.gcp.mongodb.net/otdatasb