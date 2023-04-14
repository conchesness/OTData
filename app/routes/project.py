from app import app
from flask import render_template
from flask import render_template, redirect, url_for, request, session, flash, Markup
from mongoengine import Q
from app.classes.data import User, Project, ProjectCheckin, ProjectTask, GEnrollment, GoogleClassroom
from app.classes.forms import ProjectForm, ProjectTaskForm, ProjectCheckinForm
import datetime as dt
from bson.objectid import ObjectId

def newNumberTasks(editProj,num):
    for task in editProj.tasks:
        if task.order == num:
            task.order += 1
            num += 1
    editProj.save()
    editProj.reload()
    return editProj

def reNumberTasks(editProj):
    renum = 0
    editProj.tasks.sort(key=lambda x: x.order)
    for task in editProj.tasks:
        renum += 1
        task.order = renum
    editProj.save()
    editProj.reload()
    return editProj

@app.route('/myprojects/<currProjId>/<uid>', methods=['GET', 'POST'])
@app.route('/myprojects/<currProjId>', methods=['GET', 'POST'])
@app.route('/myprojects', methods=['GET', 'POST'])
def myProjects(currProjId=None, uid=None):
    
    if currProjId:
        currProj = Project.objects.get(pk=currProjId)
    else:
        currProj=None

    if uid:
        stu = User.objects.get(id = uid)
    else:
        stu = User.objects.get(pk = session['currUserId'])

    print(stu.fname)

    myProjects = Project.objects(student = stu)
    projectForm = ProjectForm()
    projectTaskForm = ProjectTaskForm()
    projectCheckinForm = ProjectCheckinForm()

    gclasses = GEnrollment.objects(owner = stu, status="Active")
    classChoices = []
    for gClass in gclasses:
        classChoices.append((gClass.gclassroom.id,gClass.gclassroom.gclassdict['name']))
    projectForm.gclass.choices = classChoices

    workingOnChoices = []
    if currProj:
        for task in currProj.tasks:
            workingOnChoices.append((task.oid,task.name))
    projectCheckinForm.workingon.choices = workingOnChoices

    if projectForm.submitProject.data and projectForm.validate_on_submit():
        gClass = GoogleClassroom.objects.get(pk = projectForm.gclass.data)
        newProject = Project(
            name = projectForm.name.data,
            student = stu,
            gclass = gClass
        )
        newProject.save()
        return redirect(url_for('myProjects'))


    elif projectTaskForm.submitTask.data and projectTaskForm.validate_on_submit():
        currProj = newNumberTasks(currProj,projectTaskForm.order.data)
        currProj.tasks.create(
                oid = ObjectId(),
                order = projectTaskForm.order.data,
                name = projectTaskForm.name.data,
                desc = projectTaskForm.desc.data
            )
        currProj = reNumberTasks(currProj)
        currProj.save()
        return redirect(url_for('myProjects',currProjId=currProj.id))


    elif projectCheckinForm.submitCheckin.data and projectCheckinForm.validate_on_submit():
        currProj.checkins.create(
                oid = ObjectId(),
                workingon = projectCheckinForm.workingon.data,
                workingonname = currProj.tasks.get(oid=projectCheckinForm.workingon.data).name,
                status = projectCheckinForm.status.data,
                desc = projectCheckinForm.desc.data
            )
        currProj.save()
        return redirect(url_for('myProjects',currProjId=currProj.id))
    
    return render_template('projects/myprojects.html',currUser=stu,currProj=currProj,myProjects=myProjects,projectForm=projectForm, projectTaskForm=projectTaskForm, projectCheckinForm=projectCheckinForm)

@app.route('/project/delete/<pid>')
def projectDelete(pid):
    deleteProject = Project.objects.get(pk=pid)
    deleteProject.delete()
    return redirect(url_for('myProjects'))

@app.route('/project/task/delete/<pid>/<ptid>')
def projectTaskDelete(pid,ptid):
    editProject = Project.objects.get(pk=pid)
    editProject.tasks.filter(oid=ptid).delete()
    editProject = reNumberTasks(editProject)
    editProject.save()
    return redirect(url_for('myProjects',currProjId=pid))

@app.route('/project/task/edit/<pid>/<ptid>', methods=['GET', 'POST'])
def projectTaskEdit(pid,ptid):
    editProject = Project.objects.get(pk=pid)
    form = ProjectTaskForm()
    if form.submitTask.data and form.validate_on_submit():
        editProject = newNumberTasks(editProject,form.order.data)
        editProject.tasks.filter(oid=ptid).update(
            order = form.order.data,
            name = form.name.data,
            status = form.status.data,
            desc = form.desc.data
            )
        if editProject.tasks.get(oid=ptid).status == "Complete":
            editProject.tasks.filter(oid=ptid).update(
                completedate = dt.datetime.utcnow
            )
        editProject.save()
        editProject = reNumberTasks(editProject)
        return redirect(url_for('myProjects',currProjId=pid))
    
    editTask = editProject.tasks.get(oid=ptid)

    form.order.data = editTask.order
    form.name.data = editTask.name
    form.status.process_data(editTask.status)
    form.desc.data = editTask.desc

    return render_template('projects/projecttaskedit.html', form=form, editProject=editProject)

@app.route('/project/checkin/delete/<pid>/<pcid>')
def projectCheckinDelete(pid,pcid):
    editProject = Project.objects.get(pk=pid)
    editProject.checkins.filter(oid=pcid).delete()
    editProject.save()
    return redirect(url_for('myProjects',currProjId=pid))

@app.route('/project/dashboard/<gcid>')
def projectDashboard(gcid):
    gclass = GoogleClassroom.objects.get(id=gcid)
    projects = Project.objects(gclass=gclass)
    return render_template('projects/projects.html', projects=projects, gclass=gclass)