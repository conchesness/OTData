from app import app
from flask import render_template, redirect, url_for, session, flash, Markup
from app.classes.data import Transcript, User
from app.classes.forms import TranscriptForm
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import mongoengine.errors

@app.route('/transcript/delete/<tid>')
def transcriptDelete(tid):
    tObj = Transcript.objects.get(id=tid)
    currUser = User.objects.get(id=session['currUserId'])
    if tObj.student == currUser or currUser.isadmin:
        tObj.delete()
        flash("Transcript is deleted.")
    return redirect(url_for('transcriptNew'))

@app.route('/transcript/<aid>')
def transcript(aid):
    try:
        student=User.objects.get(aeriesid=aid)
    except mongoengine.errors.DoesNotExist:
        flash(f"No student with Aeries ID: {aid}")
        return redirect(url_for('transcriptNew'))
    try:
        tObj = Transcript.objects.get(student=student)
    except:
        flash(f"{student.fname} {student.lname} does not yet have a transcript on OTData.")
        return redirect(url_for('transcriptNew'))
    
    # Style and create the html
    transcriptDF = pd.DataFrame.from_dict(tObj.transcriptDF)

    # miCols = []
    # for i,col in enumerate(transcriptDF.columns):
    #     miCols.append((i,col))
    # transcriptDF.columns = pd.MultiIndex.from_tuples(miCols)

    transcriptDFHTML = transcriptDF.style\
        .format(precision=2)\
        .set_table_styles([
            {'selector': 'tr:hover','props': 'background-color: #CCCCCC; font-size: 1em;'},\
            {'selector': 'thead','props': 'height:140px'},\
            {'selector': 'th','props': 'background-color: white !important'}], overwrite=False)\
        .set_table_attributes('class="table"')  \
        .set_uuid('trans')\
        .set_sticky(axis="columns",levels=0)\
        .set_sticky(axis="index")\
        .to_html()

    transcriptDFHTML = Markup(transcriptDFHTML)

    return render_template('transcripts/transcript.html', cols=list(transcriptDF.columns), transcriptHTML = transcriptDFHTML,tObj=tObj,student=student)

@app.route('/transcript/new', methods=['GET', 'POST'])
def transcriptNew():
    form = TranscriptForm()

    if form.validate_on_submit():
        html = form.transcript.data
        soup = BeautifulSoup(html,features="html.parser")
        stuName = soup.find('span',{'class':'student-full-name'})
        # strip extra whitespace from ends and center of string
        stuName = stuName.text.strip()
        stuName = " ".join(stuName.split())
        stuID = soup.find('span',attrs={"data-tcfc":"STU.ID"})
        stuID = stuID.text
        try:
            student = User.objects.get(aeriesid = stuID)
        except:
            tObj=None
            student = {'stuName':stuName,'aeriesid':stuID}
            flash("This student is not in OTData.")
        else:
            try:
                tObj = Transcript.objects.get(student=student)
            except:
                tObj = None
            else:
                flash(f"This student already has a transcript in OTData.")
                return redirect(url_for("transcript",aid=stuID))

        results = soup.find('table',{"class":"CourseHistory"})
        all_tr = results.find_all('tr')
        transcript = []

        for tr in all_tr:
            schoolNum = tr.find('td',attrs={"data-tcfc":"HIS.ST"})
            schoolName = tr.find('span')
            grade = tr.find('td',attrs={"data-tcfc":"HIS.GR"})
            year = tr.find('td',attrs={"data-tcfc":"HIS.YR"})
            term = tr.find('td',attrs={"data-tcfc":"HIS.TE"})
            mark = tr.find('td',attrs={"data-tcfc":"HIS.MK"})
            course = tr.find('td',attrs={"data-tcfc":"CRS.CO"})
            otherCourse = tr.find('td',attrs={"data-tcfc":"HIS.CO"})
            cp = tr.find('td',attrs={"data-tcfc":"CRS.CP"})
            nh = tr.find('td',attrs={"data-tcfc":"CRS.NA"})
            cc = tr.find('td',attrs={"data-tcfc":"HIS.CC"})
            cr = tr.find('td',attrs={"data-tcfc":"HIS.CR"})

            if grade:
                txtCourse = course.text.strip()
                txtCourse = " ".join(txtCourse.split())
                if otherCourse:
                    txtOtherCourse = otherCourse.text.strip()
                    txtOtherCourse = " ".join(txtOtherCourse.split())
                row={
                    'sname':schoolName.attrs['title'],
                    'snum':schoolNum.text.strip(),
                    'grade':grade.text.strip(),
                    'year':year.text.strip(),
                    'term':term.text.strip(),
                    'mark':mark.text.strip(),
                    'course':txtCourse,
                    'altCourse':txtOtherCourse,
                    'cp':cp.text.strip(),
                    'nh':nh.text.strip(),
                    'cc':cc.text.strip(),
                    'cr':cr.text.strip()
                    }
                transcript.append(row)

        transcriptDF = pd.DataFrame.from_dict(transcript)

        transcriptDF['grade'] = pd.to_numeric(transcriptDF['grade'])
        transcriptDF = transcriptDF[transcriptDF.grade > 8]

        gp = [
            {'mark':'A+','gp':4},
            {'mark':'A','gp':4},
            {'mark':'A-','gp':4},
            {'mark':'B+','gp':3},
            {'mark':'B','gp':3},
            {'mark':'B-','gp':3},
            {'mark':'C+','gp':2},
            {'mark':'C','gp':2},
            {'mark':'C-','gp':2},
            {'mark':'D+','gp':1},
            {'mark':'D','gp':1},
            {'mark':'D-','gp':1},
            {'mark':'F+','gp':0},
            {'mark':'F','gp':0},
            {'mark':'F-','gp':0},
        ]
        gpDF = pd.DataFrame.from_dict(gp)

        transcriptDF = pd.merge(transcriptDF, 
                            gpDF, 
                            on ='mark', 
                            how ='left')
                        
        transcriptDF['cc'] = transcriptDF['cc'].astype('float64')
        transcriptDF['cr'] = transcriptDF['cr'].astype('float64')
        # Created an Adjusted Grade Points for Honors and AP whever grade is above a D
        transcriptDF['adjgp'] = np.where(((transcriptDF['nh'] == "H") | (transcriptDF['nh'] == "H/AP")) & ((transcriptDF['gp'] > 1)), transcriptDF['gp']+1, transcriptDF['gp'])
        # Remove values from adjusted grade points that are not cllege prep
        transcriptDF['adjgp'] = np.where((transcriptDF['nh'] == "N") | (transcriptDF['cp'] != "P"), np.nan, transcriptDF['adjgp'])
        transcriptDF['adjcr'] = np.where(transcriptDF['adjgp'] > 0, transcriptDF['cr'],np.nan)
        transcriptDF['countcr'] = np.where(transcriptDF['gp'] > 0, transcriptDF['cr'],np.nan)

        # Sort the data
        transcriptDF = transcriptDF.sort_values(by=['grade', 'term','snum']).reset_index(drop=True)
        # created weighted colums that multiply the credits received by the gradepoints
        transcriptDF['weightedgp'] = transcriptDF['cr']*transcriptDF['gp']
        transcriptDF['weightedadjgp'] = transcriptDF['cr']*transcriptDF['adjgp']
        # get total for numeric columns
        transcriptDF.loc['total'] = transcriptDF[['cc','cr','weightedgp','weightedadjgp','adjcr','countcr']].sum()
        # Divide weighted columns by credit earned (cc) to get weighted averages

        transcriptDF.loc['Ave'] = transcriptDF[['gp','adjgp']].mean()
        transcriptDF.at['Ave','weightedadjgp'] = transcriptDF.at['total','weightedadjgp'] / transcriptDF.at['total','adjcr']
        transcriptDF.at['Ave','weightedgp'] = transcriptDF.at['total','weightedgp'] / transcriptDF.at['total','countcr']

        # Drop the weighted columns
        # transcriptDF = transcriptDF.drop(['weightedgp','weightedadjgp'],axis=1)
        # Cleanup the NaN's
        transcriptDF[["sname","snum",'grade','year','term','cc','cr','mark','course','altCourse','cp','nh']] = transcriptDF[["sname","snum",'grade','year','term','cc','cr','mark','course','altCourse','cp','nh']].fillna('')
        transcriptDF.rename(columns={'cc': 'Credit Attempted', 'cr': 'Credit Earned', 'cp':'College Prep?','nh':'Honors-AP-Not'}, inplace=True)
            
        transcriptDF.index = transcriptDF.index.map(str)

        transcriptDict = transcriptDF.to_dict()
        tObj = Transcript(
            student=student,
            transcriptDF = transcriptDict        )
        tObj.save()
        flash("Transcipt saved to OTData.")

        return redirect(url_for('transcript',aid=stuID))
    
    return render_template('transcripts/transcript.html',form=form)
