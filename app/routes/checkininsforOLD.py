@app.route('/checkinsfor/<gclassid>/<sndrmdr>', methods=['GET', 'POST'])
@app.route('/checkinsfor/<gclassid>', methods=['GET', 'POST'])
def checkinsfor(gclassid,sndrmdr=0):
    gClassroom = GoogleClassroom.objects.get(gclassid=gclassid)
    gclassname = gClassroom.gclassdict['name']

    sndrmdr = int(sndrmdr)
    dateForm = DateForm()
    stuForm = StudentWasHereForm()

    try:
        session['searchdatetime']
    except KeyError:
        searchdate = dt.now(pytz.timezone('US/Pacific')).date()
        searchdatetime = dt(searchdate.year, searchdate.month, searchdate.day)
        session['searchdatetime'] = searchdatetime
    
    if dateForm.submitDateForm.data and dateForm.validate_on_submit():
        # get the date from the form
        searchdate = dateForm.querydate.data
        # turn the date in to a datetime 
        searchdatetime = dt(searchdate.year, searchdate.month, searchdate.day)
        session['searchdatetime'] = searchdatetime
    else:
        searchdatetime = session['searchdatetime']

    tz = pytz.timezone('US/Pacific')
    searchdatetime = tz.localize(searchdatetime)

    dateForm.querydate.data = searchdatetime.date()

    query = (Q(gclassid = gclassid) & (Q(createdate__gt = searchdatetime) & Q(createdate__lt = searchdatetime + timedelta(days=1))) )
    checkins = CheckIn.objects(query)

    if google.oauth2.credentials.Credentials(**session['credentials']).valid:
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    else:
        return redirect('/authorize')
    session['credentials'] = credentials_to_dict(credentials)
    classroom_service = googleapiclient.discovery.build('classroom', 'v1', credentials=credentials)
    students = []
    pageToken = None
    try:
        students_results = classroom_service.courses().students().list(courseId = gclassid,pageToken=pageToken).execute()
    except RefreshError:
        flash("When I asked for the courses from Google Classroom I found that your credentials needed to be refreshed.")
        return redirect('/authorize')

    while True:
        pageToken = students_results.get('nextPageToken')
        students.extend(students_results['students'])
        if not pageToken:
            break
        students_results = classroom_service.courses().students().list(courseId = gclassid,pageToken=pageToken).execute()


    # This is a list of gids for the students that checked in
    checkingids = [checkin.student.gid for checkin in checkins]

    # This is a list of gids for the students in the Google Classroom
    rostergids = [student['userId'] for student in students]

    # This is a list of gids for of students on the google roster but not in the checked in
    notcheckedingids = [rostergid for rostergid in rostergids if rostergid not in checkingids]
    
    # If there are students who did not checkin get a list of all their user objects
    notcheckedstus = []
    notcheckedstuschoices = []
    if notcheckedingids:
        for notcheckedingid in notcheckedingids:
            try:
                aStu = User.objects.get(gid = notcheckedingid)
            except:
                # Check for students that have never logged in to OTData so they don't have a gid
                # TODO check these id's back against the students 
                for stu in students:
                    if stu['userId'] == notcheckedingid and stu['profile']['emailAddress'][:2]=='s_':
                        try:
                            temp = User.objects.get(otemail = stu['profile']['emailAddress'])
                        except Exception as error:
                            flash(f"Unknown error for {stu['profile']['emailAddress']}: {error}")
                            break
                        notcheckedstus.append(temp)
                        notcheckedstuschoices.append((temp.aeriesid,Markup(f'{temp.lname}, {temp.fname}<a href="/profile/{temp.aeriesid}">&#128279;</a>')))
                        break
            else:
                if aStu.role.lower() == "student":
                    try:
                        stuGClass = aStu.gclasses.get(gclassid=gclassid)
                    except:
                        notcheckedstuschoices.append((aStu.aeriesid,Markup(f'{aStu.lname}, {aStu.fname} <a href="/profile/{aStu.aeriesid}">&#128279;</a>')))
                    else:
                        if stuGClass.sortcohort:
                            sortCohort = stuGClass.sortcohort
                            setattr(aStu, 'sortCohort', sortCohort)
                        else:
                            sortCohort = ""
                        notcheckedstuschoices.append((aStu.aeriesid,Markup(f'{sortCohort} {aStu.lname}, {aStu.fname} <a href="/profile/{aStu.aeriesid}">&#128279;</a>')))
                    notcheckedstus.append(aStu)

    # sort the list of tuples by its second item which is student's name
    lst = len(notcheckedstuschoices)  
    for i in range(0, lst):  
        for j in range(0, lst-i-1):  
            if (notcheckedstuschoices[j][1] > notcheckedstuschoices[j + 1][1]):  
                temp = notcheckedstuschoices[j]  
                notcheckedstuschoices[j]= notcheckedstuschoices[j + 1]  
                notcheckedstuschoices[j + 1]= temp  

    stuForm.student.choices = notcheckedstuschoices

    if request.form and 'submitStuForm' in request.form and len(stuForm.student.data)>0:
        for stu in stuForm.student.data:
            student = User.objects.get(aeriesid=stu)
            checkinstus(gclassid,gclassname,student,searchdatetime)
        request.form = None
        return redirect(url_for('checkinsfor', gclassid=gclassid,gclassname=gclassname)) 

    if len(notcheckedstus) > 0 and sndrmdr == 1:
        client = Client(twilio_account_sid, twilio_auth_token)
        # TODO should probably make sure these are the same timezone
        if searchdatetime.date() == dt.now(pytz.timezone('US/Pacific')).date():
            for stu in notcheckedstus:
                if stu.mobile:
                    client.messages.create(
                            body=f"Please Check in for {gclassname}.",
                            from_='+15108043552',
                            to=stu.mobile
                        )
                    flash(f'txt sent to {stu.fname} {stu.lname}.')
        else:
            flash('You can only send checkin reminders for the current day.')

    return render_template('checkinsfor.html', querydate= dateForm.querydate.data, checkins=checkins, stuForm=stuForm, dateForm=dateForm, gclassid=gclassid, gclassname=gclassname, notcheckedstus=notcheckedstus, searchdatetime=searchdatetime)
