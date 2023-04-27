from app import app
from flask import render_template, redirect, url_for, session, flash, Markup
from app.classes.data import Transcript, User
from app.classes.forms import TranscriptForm
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np


@app.route('/transcript/new', methods=['GET', 'POST'])
def transcript():
    form = TranscriptForm()

    if form.validate_on_submit():
        html = form.transcript.data
        soup = BeautifulSoup(html,features="html.parser")
        results = soup.find('table',{"class":"CourseHistory"})
        all_tr = results.find_all('tr')
        transcript = []

        for tr in all_tr:
            schoolNum = tr.find('td',attrs={"data-tcfc":"HIS.ST"})
            schoolName = tr.find('span')
            grade = tr.find('td',attrs={"data-tcfc":"HIS.GR"})
            year = tr.find('td',attrs={"data-tcfc":"HIS.YR"})
            term = tr.find('td',attrs={"data-tcfc":"HIS.TE"})
            cc = tr.find('td',attrs={"data-tcfc":"HIS.CC"})
            cr = tr.find('td',attrs={"data-tcfc":"HIS.CR"})
            mark = tr.find('td',attrs={"data-tcfc":"HIS.MK"})
            course = tr.find('td',attrs={"data-tcfc":"CRS.CO"})
            otherCourse = tr.find('td',attrs={"data-tcfc":"HIS.CO"})
            cp = tr.find('td',attrs={"data-tcfc":"CRS.CP"})
            nh = tr.find('td',attrs={"data-tcfc":"CRS.NA"})

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
                    'cc':cc.text.strip(),
                    'cr':cr.text.strip(),
                    'mark':mark.text.strip(),
                    'course':txtCourse,
                    'altCourse':txtOtherCourse,
                    'cp':cp.text.strip(),
                    'nh':nh.text.strip()
                    }
                transcript.append(row)
        pd.set_option('display.float_format', '{:.2f}'.format)

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
                            how ='inner')

        # Create Adjusted Grade Points Column
        transcriptDF['cc'] = transcriptDF['cc'].astype('float64')
        transcriptDF['cr'] = pd.to_numeric(transcriptDF['cr'])
        # Add a GP for Honors and AP whever grade is above a D
        transcriptDF['adjgp'] = np.where(((transcriptDF['nh'] == "H") | (transcriptDF['nh'] == "H/AP")) & ((transcriptDF['gp'] > 1)), transcriptDF['gp']+1, transcriptDF['gp'])
        # Remove the GP for N like PE
        transcriptDF['adjgp'] = np.where((transcriptDF['nh'] == "N") | (transcriptDF['cp'] != "P"), np.nan, transcriptDF['adjgp'])

        transcriptDF = transcriptDF.sort_values(by=['grade', 'term','sname']).reset_index(drop=True)
        transcriptDF.loc['total'] = transcriptDF[['gp','adjgp']].mean()
        transcriptDF.loc['sum'] = transcriptDF[['cc','cr']].sum()
        transcriptDF.at['total','cc'] = transcriptDF.at['sum','cc'] 
        transcriptDF.at['total','cr'] = transcriptDF.at['sum','cr'] 
        transcriptDF = transcriptDF.drop('sum')

        transcriptDF[["sname","snum",'grade','year','term','cc','cr','mark','course','altCourse','cp','nh']] = transcriptDF[["sname","snum",'grade','year','term','cc','cr','mark','course','altCourse','cp','nh']].fillna('')
        transcriptDFHTML = Markup(transcriptDF.to_html())
        transcriptDFHTML = transcriptDFHTML.replace('dataframe','table')

        return render_template('transcripts/transcript.html', form=form,transcript = transcriptDFHTML)
    
    return render_template('transcripts/transcript.html',form=form)
