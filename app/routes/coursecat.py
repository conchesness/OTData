from app import app
from flask import render_template, redirect, url_for, session, flash
from app.classes.data import User, Section, Course
from app.classes.forms import CourseForm, SectionForm
import datetime as d
from mongoengine import Q

@app.route("/ccteachers/<sort>")
@app.route("/ccteachers")
def teachers(sort="lname,fname"):
    teachers=User.objects(role__iexact="teacher")
    return render_template("coursecat/teachers.html",teachers=teachers, sort=sort)

@app.route("/sections/<teacherid>")
def teachersections(teacherid):
    teacher = User.objects.get(pk=teacherid)
    sections = Section.objects(teacher=teacher)
    return render_template('coursecat/teachersections.html',sections=sections,teacher=teacher)

@app.route("/cccourses/<page>",methods=['GET','POST'])
@app.route("/cccourses", methods=['GET','POST'])
def courses(page=1):
    form=CourseForm()
    page=int(page)
    ignore=['Y3801','Y8301','Z4101']
    courses = Course.objects(aeriesnum__nin = ignore).paginate(page=page, per_page=10)

    if form.validate_on_submit():
        q = Q(aeriesnum__exists=True)

        if form.dept.data:
            q1 = Q(dept=form.dept.data)
        else:
            q1 = None

        if form.atog.data:
            q2 = Q(atog=form.atog.data)
        else:
            q2 = None

        if form.level.data:
            q3 = Q(atog=form.level.data)
        else:
            q3 = None

        if form.notupdated.data:
            q4 = Q(name__exists=False)
        else:
            q4 = None

        if form.aeriesnum.data:
            q5 = Q(aeriesnum__iexact=form.aeriesnum.data)
        else:
            q5 = None

        if form.aeriesname.data:
            q6 = Q(aeriesname__icontains=form.aeriesname.data)
        else:
            q6 = None

        query = q & q1 & q2 & q3 & q4 & q5 & q6
        
        courses=Course.objects(query).paginate(page=page, per_page=10)

    return render_template("coursecat/courses.html",courses=courses,form=form)

@app.route('/cccourse/<coursenum>')
def course(coursenum):
    course=Course.objects.get(aeriesnum=coursenum)
    sections=Section.objects(course=course)

    return render_template("coursecat/course.html",course=course, sections=sections)

@app.route('/cccoursenew', methods=['GET', 'POST'])
def cccoursenew():
    if session['role'].lower() == "student" and not session['courseCatAdmin']:
        flash(f"Your role is {session['role']}. You don't have access to edit courses.")
        return redirect(url_for('cccourses'))

    form=CourseForm()

    if form.validate_on_submit():
        newCourse = Course(
            aeriesname = form.aeriesname.data,
            aeriesnum = form.aeriesnum.data,
            name = form.name.data,
            dept = form.dept.data,
            atog = form.atog.data,
            level = form.level.data
        )
        newCourse.save()
        return redirect(url_for('course',coursenum=newCourse.aeriesnum))

    return render_template('coursecat/courseedit.html', form=form)

@app.route('/cccourseedit/<coursenum>', methods=['GET', 'POST'])
def courseedit(coursenum):
    if session['role'].lower() == "student" and not session['courseCatAdmin']:
        flash(f"Your role is {session['role']}. You don't have access to edit courses.")
        return redirect(url_for('course',coursenum=coursenum))

    editCourse=Course.objects.get(aeriesnum=coursenum)
    form=CourseForm()

    if form.validate_on_submit():
        editCourse.update(
            name = form.name.data,
            dept = form.dept.data,
            atog = form.atog.data,
            level = form.level.data
        )
        editCourse.save()
        return redirect(url_for('course',coursenum=coursenum))

    form.name.data = editCourse.name
    form.level.data = editCourse.level
    form.dept.data = editCourse.dept
    form.atog.data = editCourse.atog

    return render_template('coursecat/courseedit.html', course=editCourse, form=form)

@app.route('/ccteacherclass/<tnum>/<cnum>')
def teacherclass(tnum,cnum):
    teacher=User.objects.get(tnum=tnum)
    course=Course.objects.get(aeriesnum=cnum)
    section=Section.objects.get(course=course,teacher=teacher)
    
    return render_template('coursecat/teacherclass.html',section=section)

@app.route('/ccteacherclassedit/<tnum>/<cnum>', methods=['GET', 'POST'])
def teacherclassedit(tnum,cnum):

    if session['role'].lower() == 'student' and not session['courseCatAdmin'] and not session['isadmin']:
        flash(f"You can't edit that section as a student.")
        return redirect(url_for('teacherclass',tnum=tnum,cnum=cnum))
    teacher=User.objects.get(tnum=tnum)
    course=Course.objects.get(aeriesnum=cnum)
    section=Section.objects.get(course=course,teacher=teacher)
    currUser = User.objects.get(pk=session['currUserId'])
    print(not session['courseCatAdmin'] and not session['isadmin'])
    if not currUser == section.teacher and not session['courseCatAdmin'] and not session['isadmin']:
        flash(f"You can't edit that section because it is not yours.")
        return redirect(url_for('teacherclass',tnum=tnum,cnum=cnum))
    
    form = SectionForm()
    
    if form.validate_on_submit():
        if not form.url.data:
            form.url.data=None
        if not form.yearinschool.data:
            form.yearinschool.data=None

        section.update(
            url=form.url.data,
            desc=form.desc.data,
            pathway=form.pathway.data,
            yearinschool=form.yearinschool.data,
            modified=d.datetime.utcnow()
        )

        return redirect(url_for('teacherclass',tnum=tnum,cnum=cnum))
    
    form.url.data=section.url
    form.desc.data=section.desc
    form.pathway.data=section.pathway
    form.yearinschool.data=section.yearinschool

    return render_template('coursecat/teacherclassedit.html',form=form,section=section)