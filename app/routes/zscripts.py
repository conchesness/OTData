from app import app
from flask import render_template, redirect, flash
from app.classes.data import User, Adult, User, Course, Section, Config
import pandas as pd
import time

# A script that is supposed to remove a field from the MongoDB
# @app.route('/unsetadults')
# def unseradults():
#     users=User.objects()
#     users.update({}, {"$unset": {"adults": 1}}, multi=True)
#     return redirect('/')

## Scripts for getting Aeries ID's ###
##This script takes a csv of students and edits aeries records or creates a new aeries record.
##This script just replaces all the data with new data on an edit.
@app.route('/aeriesstudentimport')
def aeriesstudentimport():
    # TODO: need to add gpa to csv and import script
    settings = Config.objects.first()
    if settings.devenv == False:
        flash(f"You can only run scripts in a local environment.")
        return redirect('/')

    # This reads a csv file in to a dataframe
    df_aeries = pd.read_csv('csv/aeries.csv')
    df_aeries.fillna('', inplace=True)

    #  This turns that dataframe in to a python dictionary
    students = df_aeries.to_dict(orient='records')

    # This iteratates through the students dict
    for index, student in enumerate(students):
        # Using the aeriesId as the unique ID, if the Aeries record exists, update all values

        try:
            editAeries = User.objects.get(aeriesid = int(student['aeriesID']))
            edit = True
        except:
            edit = False

        if edit:
            editAeries.update(
                afname = student['afname'],
                alname = student['alname'],
                aphone = student['aphone'],
                azipcode = student['zipcode'],
                astreet = student['street'],
                acity = student['city'],
                astate = student['state'],
                aadults = student['adults'],
                aadultemail = student['adultemail'],
                aadult1phone = student['adult1phone'],
                aadult2phone = student['adult2phone'],
                agender = student['gender'],
                grade = student['grade'],
                aethnicity = student['ethnicity'],
                cohort = student['academy'],
                langflu = student['langflu'],
                sped = student['sped'],
                gpa = student['gpa'],
                role = 'student'
            )
            print(f"{index}: {editAeries.otemail} edited")
        else:
            # If the Aeries record does not exist, create it using the values in the dictionary
            newAeries = User(
                aeriesid = student['aeriesID'],
                otemail = student['email'],
                afname = student['afname'],
                alname = student['alname'],
                aphone = student['aphone'],
                azipcode = student['zipcode'],
                astreet = student['street'],
                acity = student['city'],
                astate = student['state'],
                aadults = student['adults'],
                aadultemail = student['adultemail'],
                aadult1phone = student['adult1phone'],
                aadult2phone = student['adult2phone'],
                agender = student['gender'],
                grade = student['grade'],
                aethnicity = student['ethnicity'],
                cohort = student['academy'],
                langflu = student['langflu'],
                sped = student['sped'],
                gpa = student['gpa'],
                role = 'student'
            ).save()
            print(f'{index}: {newAeries.otemail} created')
    return render_template('index.html')


@app.route('/addallaeriesteachers')
def addallaeriesTeachers():
    settings = Config.objects.first()
    if settings.devenv == False:
        flash(f"You can only run scripts in a local environment.")
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
        flash(f"You can only run scripts in a local environment.")
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
        flash(f"You can only run scripts in a local environment.")
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

@app.route('/addaeriescourses')
def addaeriescourses():
    start_time = time.time()

    # This reads a csv file in to a dataframe
    df_aeriesenrollments = pd.read_csv('aeriesenrollments.csv')
    df_aeriesenrollments.fillna('', inplace=True)

    #  This turns that dataframe in to a python dictionary
    aeriesenrollments = df_aeriesenrollments.to_dict(orient='records')
    total = len(aeriesenrollments)

    for index, enrollment in enumerate(aeriesenrollments):
        editAeries = Aeries.objects.get(aeriesId=enrollment['aeriesId'])
        addSection = Aeriessection.objects.get(sectionnum=enrollment['sectionnum'])
        editAeries.update(add_to_set__aeriesclasses = addSection)
        if index % 10 == 0:
            print(f'{index} of {total} in {(time.time() - start_time)/60} mins')

    flash(f"total mins was {(time.time() - start_time)/60}")
    
    return render_template('index.html')



@app.route('/addusertoaeriesteacher')
def addusertoaeriesteacher():
    aeriesTeachers = Teacher.objects()
    for teacher in aeriesTeachers:
        try:
            teacherUser = User.objects.get(email = teacher.email)
            print(f"{teacherUser.gfname} is a User")
            teacher.reload()
            print("reload Teacher Record")
            teacher.update(
                user = teacherUser
            )
            print(f"{teacher.aeriesname} User is saved on Teacher record")
            print()
        except:
            print(f"{teacher.aeriesname} is not a User")
            print()

    return redirect('/')

# This script connect the sections table to the teachers table
@app.route('/addsectionstoteacher')
def addsectiontoteacher():
    allsects = Aeriessection.objects()
    l=len(allsects)
    for i,sect in enumerate(allsects):
        try:
            teacher = Teacher.objects.get(teachernum=sect.teachernum)
            teacher.update(add_to_set__sections = sect)
            sect.update(teacherref = teacher)
            print(f"{i}/{l}: {sect.sectionnum} {sect.course} added to {teacher.fname} {teacher.lname} and vide versa ")
        except:
            flash(f"Couldn't find teachernum: {sect.teachernum}")
    return redirect('/')

# This script finds the missing teachers that are in sections but not in teachers
@app.route('/findmissingteachers')
def findmissingteachers():
    sections = Aeriessection.objects()
    l=len(sections)
    for i,section in enumerate(sections):
        try:
            teacher = Teacher.objects.get(teachernum=section.teachernum)
        except:
            newTeacher = Teacher(
                teachernum = section.teachernum,
                aeriesname = section.teacher
            )
            newTeacher.save()
            print(f"created {newTeacher.teachernum} {newTeacher.aeriesname}")
    return redirect('/')
