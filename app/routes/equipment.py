from flask.helpers import url_for
from app import app
from flask import render_template, redirect, session, flash
from app.classes.data import Equipment, User
from app.classes.forms import ComputerForm
from  datetime import datetime, date

@app.route('/comp/list')
def complist():
    computers = Equipment.objects()
    print(computers)
    return (render_template('computers.html', computers = computers))

@app.route('/comp/new', methods=['GET', 'POST'])
def compnew():
    form = ComputerForm()

    if form.validate_on_submit():

        if not form.status.data.lower() == "working" and len(form.statusdesc.data) == 0:
            flash(f"With status of {form.status.data} you must include a ststus description.")
            return redirect(url_for('compnew'))

        compNew = Equipment(
            type = form.equiptype.data,
            location = form.location.data,
            uid = form.idnum.data,
            stickernum = str(form.stickernum.data),
            statusdesc = form.statusdesc.data,
            status = form.status.data,
            editdate = datetime.utcnow()
        )

        compNew.save()

        return redirect(url_for('complist'))

    return render_template('computerform.html', form=form)

@app.route('/comp/del/<compid>')
def compdel(compid):

    compDel = Equipment.objects.get(pk=compid)

    compDel.delete()
    flash(f"The record for computer ID#: {compDel.uid} has been deleted.")

    return redirect(url_for('complist'))


@app.route('/compborrow/<aeriesid>', methods=['GET', 'POST'])
def compborrow(aeriesid):
    form = ComputerForm()

    # make sure a student can't check out a computer to another student and
    # a teacher can
    if session['role'].lower() == 'student' and session['aeriesid'] != aeriesid:
        aeriesid = session['aeriesid']

    currUser = User.objects.get(aeriesid = aeriesid)

    if form.validate_on_submit():
        if form.equiptype.data == "Thinkpad" and len(form.idnum.data) != 10:
            flash('Unique ID for a Thinkpad must be 10 characters long')
            return render_template('computerform.html',form=form,currUser=currUser)
        if form.equiptype.data[:4] == "Dell" and len(form.idnum.data) != 7:
            flash('Unique ID for a Dell must be 7 characters long')
            return render_template('computerform.html',form=form,currUser=currUser)

        if not currUser.compdateout:
            dateout = datetime.utcnow().date()
        else:
            dateout = None

        currUser.update(
            compequiptype = form.equiptype.data,
            compidnum = form.idnum.data,
            compstickernum = form.stickernum.data,
            compstatusdesc = form.statusdesc.data,
            compstatus = form.status.data,
            compdateout = dateout
        )
        return redirect(f'/profile/{currUser.aeriesid}#compborrow')
    
    form.equiptype.data = currUser.compequiptype
    form.idnum.data = currUser.compidnum
    form.stickernum.data = currUser.compstickernum
    form.statusdesc.data = currUser.compstatusdesc
    form.status.data = currUser.compstatus

    return render_template('computerform.html',form=form,currUser=currUser)

@app.route('/compdelete/<aeriesid>')
def compdelete(aeriesid):

    if session['role'].lower() == 'student' and session['aeriesid'] != aeriesid:
        aeriesid = session['aeriesid']

    currUser = User.objects.get(aeriesid=aeriesid)

    if currUser.compequiptype:
        #delete the fileds for the computer from this student
        currUser.update(
            unset__compequiptype = 1,
            unset__compidnum = 1,
            unset__compstickernum = 1,
            unset__compstatusdesc = 1,
            unset__compstatus = 1,
            unset__compdateout = 1
        )
    else:
        flash("This user doesn't have a computer checked out.")

    return redirect(f'/profile/{currUser.aeriesid}#compborrow')

@app.route('/complistall')
def complistall():
    usercomps = User.objects(compequiptype__exists=True, compequiptype__ne=None)
    if len(usercomps) > 0:
        compslist = []
        for user in usercomps:
            comp = []
            comp.append("Student: "+user.fname+" "+user.lname) 
            comp.append(user.compequiptype) 
            comp.append(user.compidnum) 
            comp.append(f"sticker#: {user.compstickernum}") 
            comp.append(f"Date checked out: {user.compdateout}") 
            comp.append(f"Date returned: {user.compdatereturned}") 
            comp.append("Status: "+user.compstatus) 
            comp.append(user.compstatusdesc) 
            compslist.append(comp)
    else:
        emptyarray=["No Computers are Checked out."]
        return render_template('array.html', array=emptyarray, nested=False)

    return render_template('array.html', array=compslist, nested=True)