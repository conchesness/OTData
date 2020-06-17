from flask_wtf import FlaskForm
from wtforms.fields.html5 import URLField, DateField
from wtforms_components import TimeField
from wtforms.validators import url, NumberRange, Email, Optional
from wtforms import widgets, SelectMultipleField, StringField, SubmitField, validators, TextAreaField, HiddenField, IntegerField, SelectField, FileField
from wtforms.fields.html5 import EmailField

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class UserForm(FlaskForm):
    fname = StringField("First Name")
    lname = StringField("Last Name")
    pronouns = SelectField(choices=[('He/Him', 'He/Him'),('She/Her','She/Her'),('They/Them','They/Them'),('Any/All','Any/All')])
    image = FileField('Avatar')
    birthdate = DateField()
    personalemail = EmailField('Personal Email')
    mobile = IntegerField(validators=(validators.Optional(),))
    ustreet = TextAreaField()
    ucity = StringField()
    ustate = StringField()
    uzipcode = IntegerField(validators=(validators.Optional(),))
    altphone = IntegerField(validators=(validators.Optional(),))
    ugender = TextAreaField()
    uethnicity = MultiCheckboxField(choices=[("Decline to say","Decline to say"),('American Indian or Alaskan Native','American Indian or Alaskan Native'), ('Asian Indian','Asian Indian'), ('Black or African American','Black or African American'), ('Cambodian','Cambodian'), ('Chinese','Chinese'), ('Filipino','Filipino'), ('Guamanian','Guamanian'), ('Hawaiian','Hawaiian'), ('Hispanic or Latino','Hispanic or Latino'), ('Hmong','Hmong'), ('Japanese','Japanese'), ('Korean','Korean'), ('Laotian','Laotian'), ('Samoan','Samoan'), ('Vietnamese','Vietnamese'), ('White','White')])
    uethnicityother = TextAreaField()
    submit = SubmitField("Submit")

class AdultForm(FlaskForm):
    fname = StringField()
    lname = StringField()
    relation = StringField()
    mobile = IntegerField(validators=(validators.Optional(),))
    altphone = IntegerField(validators=(validators.Optional(),))
    email = EmailField()
    altemail = EmailField()
    street = TextAreaField()
    city = StringField()
    state = StringField()
    zipcode = IntegerField(validators=(validators.Optional(),))
    notes = TextAreaField()
    submit = SubmitField("Submit")

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