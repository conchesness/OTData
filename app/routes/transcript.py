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
        stuName = soup.find('span',{'class':'student-full-name'})
        stuName = stuName.text.strip()
        stuName = " ".join(stuName.split())

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

        pd.set_option('display.float_format', '{:.3f}'.format)

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
        
        print(transcriptDF)
        
        transcriptDF['cc'] = transcriptDF['cc'].astype('float64')
        transcriptDF['cr'] = transcriptDF['cr'].astype('float64')
        # Created an Adjusted Grade Points for Honors and AP whever grade is above a D
        transcriptDF['adjgp'] = np.where(((transcriptDF['nh'] == "H") | (transcriptDF['nh'] == "H/AP")) & ((transcriptDF['gp'] > 1)), transcriptDF['gp']+1, transcriptDF['gp'])
        # Remove values from adjusted grade points that are not cllege prep
        transcriptDF['adjgp'] = np.where((transcriptDF['nh'] == "N") | (transcriptDF['cp'] != "P"), np.nan, transcriptDF['adjgp'])
        # Sort the data
        transcriptDF = transcriptDF.sort_values(by=['grade', 'term','snum']).reset_index(drop=True)
        # created weighted colums that multiply the credits received by the gradepoints
        transcriptDF['weightedgp'] = transcriptDF['cc']*transcriptDF['gp']
        transcriptDF['weightedadjgp'] = transcriptDF['cc']*transcriptDF['adjgp']
        # get total for numeric columns
        transcriptDF.loc['total'] = transcriptDF[['cc','cr','weightedgp','weightedadjgp']].sum()
        # Divide weighted columns by credit earned (cc) to get weighted averages

        transcriptDF.loc['Ave'] = transcriptDF[['gp','adjgp']].mean()
        transcriptDF.at['Ave','weightedadjgp'] = transcriptDF.at['total','weightedadjgp'] / transcriptDF.at['total','cc']
        transcriptDF.at['Ave','weightedgp'] = transcriptDF.at['total','weightedgp'] / transcriptDF.at['total','cc']


        # Drop the weighted columns
        #transcriptDF = transcriptDF.drop(['weightedgp','weightedadjgp'],axis=1)
        # Cleanup the NaN's
        transcriptDF[["sname","snum",'grade','year','term','cc','cr','mark','course','altCourse','cp','nh','gp','adjgp']] = transcriptDF[["sname","snum",'grade','year','term','cc','cr','mark','course','altCourse','cp','nh','gp','adjgp']].fillna('')
        # create the html
        transcriptDFHTML = Markup(transcriptDF.to_html())
        transcriptDFHTML = transcriptDFHTML.replace('dataframe','table')

        return render_template('transcripts/transcript.html', form=form,transcript = transcriptDFHTML,stuName=stuName)
    
    return render_template('transcripts/transcript.html',form=form)
