from typing import Text
from flask_wtf import FlaskForm
from wtforms.fields.html5 import URLField, DateField, DateTimeField, EmailField
from wtforms.widgets.core import Select
from wtforms_components import TimeField
from wtforms.validators import URL, NumberRange, Email, Optional, InputRequired
from wtforms import widgets, SelectMultipleField, StringField, SubmitField, validators, TextAreaField, HiddenField, IntegerField, SelectField, FileField, BooleanField
import datetime as d
import pytz

class SimpleForm(FlaskForm):
    field = TextAreaField()
    submit = SubmitField("Submit")

class DateForm(FlaskForm):
    querydate = DateField("Date", id="queryDate")
    submitDateForm = SubmitField("Submit", id="submitDateForm")

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class StudentWasHereForm(FlaskForm):
    #student = MultiCheckboxField(choices=[])
    student = MultiCheckboxField('Students:')
    submitStuForm = SubmitField("Submit",id="submitStuForm")

class SendemailForm(FlaskForm):
    to = MultiCheckboxField(choices=[])
    cc = MultiCheckboxField(choices=[])
    otherto = StringField()
    from_ = EmailField('From',validators=[(validators.Optional()),(Email())])
    subject = StringField()
    body = TextAreaField()
    submit = SubmitField("Submit")

class TxtMessageForm(FlaskForm):
    to = StringField("To")
    body = TextAreaField("Message")
    submit = SubmitField("Send")

class StudentNoteForm(FlaskForm):
    content = TextAreaField("Note:")
    type_ = SelectField("Type:",choices=[('---','---'),('Mtg', 'Mtg'),('Call','Call'),('Note','Note')])
    date = DateField(default=d.datetime.now(pytz.timezone('US/Pacific')))
    submit = SubmitField("Submit")

class StudentForm(FlaskForm):
    fname = StringField("First Name")
    lname = StringField("Last Name")
    aeriesid = IntegerField(validators=[(validators.Optional()),(NumberRange(min=100000, max=999999, message="Must be a 6 digit number."))])
    submit = SubmitField("Submit")

class CheckInForm(FlaskForm):
    desc = TextAreaField("What are you working on?",validators=[InputRequired()])
    gclassid = SelectField(choices=[],validators=[InputRequired()])
    gclassname = StringField()
    status = SelectField("How are you?",choices=[('','---'),('5','Great'),('4','Good'),('3','OK'),('2','Bad'),('1', 'Horrible')])
    synchronous = SelectField(id="synchronous",choices=[('synchronous','synchronous'),('asynchronous','asynchronous')])
    camera = SelectField(id="cameraoff",choices=[("on","on"),("off","off")])
    cameraoffreason = SelectField("Why do you want your camera off today for this class?",id="cameraoffreason",choices=[('','---'),('poor bandwidth','poor bandwidth'),('zoom fatigue','zoom fatigue'),('visual distraction','visual distraction'),('my current environment','current environment'),('other','other')])
    cameraoffreasonother = TextAreaField(id="cameraoffreasonother")
    submit = SubmitField('Submit')

class GClassForm(FlaskForm):
    classname = StringField()
    status = SelectField("Status:",choices=[('Active','Active'),('Inactive','Inactive'),('Ignore','Ignore')])
    submit = SubmitField()

class UserForm(FlaskForm):
    fname = StringField("First Name")
    lname = StringField("Last Name")
    image = FileField("Image")
    ufname = StringField("First Name")
    ulname = StringField("Last Name")
    #pronouns = SelectField(choices=[('---','---'),('He/Him', 'He/Him'),('She/Her','She/Her'),('They/Them','They/Them'),('Any/All','Any/All')])
    pronouns = StringField()
    birthdate = DateField()
    personalemail = EmailField('Personal Email',validators=[(validators.Optional()),(Email())])
    mobile = StringField()
    ustreet = TextAreaField()
    ucity = StringField()
    ustate = StringField()
    uzipcode = IntegerField(validators=[(validators.Optional()),(NumberRange(min=10000, max=99999, message="Must be a 5 digit number."))])
    #altphone = IntegerField(validators=[(validators.Optional()),(NumberRange(min=1000000000, max=9999999999, message="Must be a 7 digit number with no space or other characters."))])
    altphone = StringField()
    ugender = TextAreaField()
    uethnicity = MultiCheckboxField(choices=[("Decline to say","Decline to say"),('American Indian or Alaskan Native','American Indian or Alaskan Native'), ('Asian Indian','Asian Indian'), ('Black or African American','Black or African American'), ('Cambodian','Cambodian'), ('Chinese','Chinese'), ('Filipino','Filipino'), ('Guamanian','Guamanian'), ('Hawaiian','Hawaiian'), ('Hispanic or Latino','Hispanic or Latino'), ('Hmong','Hmong'), ('Japanese','Japanese'), ('Korean','Korean'), ('Laotian','Laotian'), ('Samoan','Samoan'), ('Vietnamese','Vietnamese'), ('White','White')])
    uethnicityother = TextAreaField()
    shirtsize = SelectField("Unisex Shirt Size", choices=[('','---'),('xs','xs'),('sm','sm'),('med','med'),('lg','lg'),('xl','xl'),('xxl','xxl'),('3xl','3xl'),('4xl','4xl')])
    linkedin = URLField()
    submit = SubmitField("Submit")

class AdultForm(FlaskForm):
    preferredcontact = BooleanField()
    fname = StringField()
    lname = StringField()
    relation = StringField()
    mobile = StringField()
    altphone = StringField()
    email = EmailField(validators=[(validators.Optional()),(Email())])
    altemail = EmailField(validators=[(validators.Optional()),(Email())])
    street = TextAreaField()
    city = StringField()
    state = StringField()
    zipcode = IntegerField(validators=[(validators.Optional()),(NumberRange(min=10000, max=99999, message="Must be a 5 digit number."))])
    notes = TextAreaField()
    primarylang = StringField()
    needstranslation = BooleanField()
    submit = SubmitField("Submit")

class CompBorrowForm(FlaskForm):
    equiptype = SelectField(choices=[(None,'---'),('Thinkpad','Thinkpad'),('Dell102','Dell Room 102 (Wright)'),('Dell104','Dell Room 104 (Ong)'),('Dell105','Dell Room 105 (Ketcham)')],validators=[InputRequired()])
    idnum = StringField('ID Number on the Equipment:',validators=[InputRequired()])
    stickernum = IntegerField('Number on a sticker:',validators=[(validators.Optional())])
    statusdesc = TextAreaField('Description',validators=[(validators.Optional())])
    status = SelectField(choices=[(None,'---'),('Working','Working'),('Problem','Problem'),('Not Working','Not Working')])
    submit = SubmitField('Submit')

class CommentForm(FlaskForm):
    content = TextAreaField("Comment")
    submit = SubmitField("Submit")

class PostForm(FlaskForm):
    subject = StringField("Title")
    body = TextAreaField("Body")
    submit = SubmitField("Submit")

class EventForm(FlaskForm):
    title = StringField("Title")
    desc = StringField("Description")
    date = DateField("Date", format='%Y-%m-%d')
    time = TimeField("Time")
    submit = SubmitField("Submit")

class FeedbackForm(FlaskForm):
    url = StringField()
    subject = StringField('Subject')
    body = TextAreaField('Description')
    solution = TextAreaField('Solution')
    status = SelectField("Status", choices=[('4-New','4-New'),('1-In Progress','1-In Progress'),('2-Complete','2-Complete'),('3-Maybe Someday','3-Maybe Someday')], default='4-New')
    priority = SelectField("Priority", choices=[('1-High','1-High'),('2-Medium','2-Medium'),('3-Low','3-Low')], default='3-Low')
    submit = SubmitField('Submit')

class CohortForm(FlaskForm):
    cohort = SelectField("Cohort", choices=[("","Unknown"),('No Academy','No Academy'),('Oakland Tech - Computer Academy','Oakland Tech - Computer Academy'),('Oakland Tech-Engineering Academy','Oakland Tech-Engineering Academy'),('Oakland Tech - Fashion, Art and Design Academy (All)','Oakland Tech - Fashion, Art and Design Academy (All)'),('Oakland Tech - Fashion, Arts, & Design Academy (CPA)','Oakland Tech - Fashion, Arts, & Design Academy (CPA)'),('Oakland Tech - Health Academy','Oakland Tech - Health Academy'),('Oakland Tech - Race, Policy and Law Academy','Oakland Tech - Race, Policy and Law Academy'),('Oakland Tech-9th Grade Janus','Oakland Tech-9th Grade Janus'),('Oakland Tech-9th Grade Neptune','Oakland Tech-9th Grade Neptune'),('Oakland Tech-9th Grade Sol','Oakland Tech-9th Grade Sol')])
    casemanager = SelectField(choices=[('','---'),('Jelani Noble', 'Jelani Noble')])
    submit = SubmitField('Submit')

class ListQForm(FlaskForm):
    cohort = MultiCheckboxField("Cohort: ", choices=[])
    grade = MultiCheckboxField("Grade: ", choices=[])
    gender = MultiCheckboxField("Gender: ", choices=[])
    ethnicity = MultiCheckboxField("Ethnicity: ", choices=[])
    submit = SubmitField("Submit")

class SortOrderCohortForm(FlaskForm):
    sortOrderCohort = SelectField("Sort Value:",validate_choice=False)
    gid = HiddenField()
    gclassid = HiddenField()
    order = HiddenField()
    submit = SubmitField("Submit")

class PlanThemeForm(FlaskForm):
    name = StringField("Name: ",validators=[InputRequired()])
    timeframe = SelectField("Timeframe: ",choices=[('','----'),('Year','Year'),('Semester','Semester'),('Season','Season')])
    description = TextAreaField("Description: ",validators=[InputRequired()])
    old = BooleanField("Old")
    submit = SubmitField("Submit")

class PlanSettingsForm(FlaskForm):
    timeframe = SelectField("Time Frame", choices=[(None,'---'),('Season','Season'),('Semester','Semester'),('Year','Year')], validators=[InputRequired()])
    yearbegin = DateField("Year Begin", validators=[InputRequired()])
    summerbegin = DateField("Semester Summer Begin", validators=[InputRequired()])
    seasonwinterbegin = DateField("Winter Begin", validators=[InputRequired()])
    seasonspringbegin = DateField("Spring Begin", validators=[InputRequired()])
    semestertwobegin = DateField("Semester Two Begin", validators=[InputRequired()])
    submit = SubmitField("Submit")

class PlanInterventionForm(FlaskForm):
    status = SelectField("Status: ", choices=[('New','New'),('In Progress','In Progress'),('Flagged','Flagged'),('Monitorring','Monitorring'),('Complete','Complete')])
    type_ = SelectField("Intervention: ", choices=[('Tutoring','Tutoring'),('Case Manager','Case Manager'),('Other','Other')])
    statusother = StringField("Other: ")
    description = TextAreaField("Description: ")
    submit = SubmitField("Submit")

class PlanIdealOutcomeForm(FlaskForm):
    name = StringField("Name: ",validators=[InputRequired()])
    description = TextAreaField("Description: ",validators=[InputRequired()])
    example = TextAreaField("Example",validators=[InputRequired()])
    submit = SubmitField("Submit")

class PlanCheckinForm(FlaskForm):
    todayfocus = SelectField(choices="",validators=[InputRequired()])
    yesterdayrating = SelectField(choices=[(0,'--'),(4,4),(3,3),(2,2),(1,1)],validate_choice=False)
    yesterdaynarrative = TextAreaField()
    todaynarrative = TextAreaField(validators=[InputRequired()])
    submit = SubmitField("Submit")

class CourseForm(FlaskForm):
    aeriesname = StringField('Aeries Name:')
    aeriesnum = StringField('Aeries #:')
    name = StringField('Course Name:')
    dept = SelectField("Department: ", choices=[("","----"),('Math','Math'),('Science','Science'),('CTE','CTE'),('PE','PE'),('English/Language Arts','English/Language Arts'),('Social Studies','Social Studies'),('Art','Art-visual and performing'),('World Languages','World Lqanguages'),('SPED','SPED'),('ELD','English Language Development'),('Computer Science','Computer Science')])
    atog = SelectField('A - G: ', choices=[("","----"),('A-History','A-History'),('B-English','B-English'),('C-Math','C-Math'),('D-Science','D-Science'),('E-Language','E-Language other than English'),('F-Art','F-Visual and performaing arts'),('G-Elective','G-College-preparatory elective')])
    level = SelectField("Level: ", choices=[("","----"),('CP','College Prep'),('HP','Honors'),('AP','Advanced Placement')])
    notupdated = BooleanField("Edited?")
    aeriesnum = StringField("Aeries Number")
    aeriesname = StringField("Aeries Name")
    pathway = SelectField("Pathway",validators=[(validators.Optional())], choices=[('','----'),('Computer','Computer'),('Engineering','Engineering'),('Fashion, Art, Design and Animation','Fashion, Art, Design and Animation'),('Health','Health'),('Race, Policy and Law','Race, Policy and Law')])
    yearinschool = MultiCheckboxField("Year",validators=[(validators.Optional())],choices=[("9th","9th"),("10th","10th"),("11th","11th"),("12th","12th")])
    submit = SubmitField('Submit')

class SectionForm(FlaskForm):
    pers = MultiCheckboxField('Periods',choices=[(0,0),(1,1),(2,2),(3,3),(4,4),(5,5),(6,6),(7,7),(8,8)])
    url = URLField('URL: ')
    desc = TextAreaField('Description: ')
    pathway = SelectField("Pathway", choices=[('','----'),('Computer','Computer'),('Engineering','Engineering'),('Fashion, Art, Design and Animation','Fashion, Art, Design and Animation'),('Health','Health'),('Race, Policy and Law','Race, Policy and Law')])
    prereq = TextAreaField('Prerequisites: ')
    yearinschool = MultiCheckboxField('Year: ',choices=[("9th","9th"),("10th","10th"),("11th","11th"),("12th","12th")])
    # modified = BooleanField("Modified?: ") # Mark this modified to update the last modified date so users know it has been updated for this year.
    submit = SubmitField('Submit')

class GroupsForm(FlaskForm):
    name = StringField('Group Name')
    desc = TextAreaField('Group Description')
    students = TextAreaField('Students')
    submit = SubmitField('Submit')

class PostGradForm(FlaskForm):
    type_ = SelectField("Type", validators=[InputRequired()], choices=[("","----"), ("Work","Work"), ("Gap Year","Gap Year"), ("2yr College","2yr College"),("4yr College","4yr College"),("Trade School","Trade School")])
    org = StringField(validators=[InputRequired()])
    link = URLField(validators=[(validators.Optional()),(URL())])
    major = StringField(validators=[(validators.Optional())])
    graduated = BooleanField(validators=[(validators.Optional())])
    desc = TextAreaField(validators=[(validators.Optional())])
    yr_started = IntegerField(validators=[InputRequired()])
    yr_ended = IntegerField(validators=[(validators.Optional())])
    pg_st_address = TextAreaField(validators=[(validators.Optional())])
    pg_city = StringField(validators=[(validators.Optional())])
    pg_state = StringField(validators=[(validators.Optional())])
    pg_zip = IntegerField(validators=[(validators.Optional())])
    submit = SubmitField("Submit")