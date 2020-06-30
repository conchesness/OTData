from flask_wtf import FlaskForm
from wtforms.fields.html5 import URLField, DateField
from wtforms_components import TimeField
from wtforms.validators import url, NumberRange, Email, Optional
from wtforms import widgets, SelectMultipleField, StringField, SubmitField, validators, TextAreaField, HiddenField, IntegerField, SelectField, FileField
from wtforms.fields.html5 import EmailField

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class SendemailForm(FlaskForm):
    to = MultiCheckboxField(choices=[])
    cc = MultiCheckboxField(choices=[])
    otherto = StringField()
    from_ = EmailField('From',validators=[(validators.Optional()),(Email())])
    subject = StringField()
    body = TextAreaField()
    submit = SubmitField("Submit")

class StudentForm(FlaskForm):
    fname = StringField("First Name")
    lname = StringField("Last Name")
    submit = SubmitField("Submit")

class UserForm(FlaskForm):
    fname = StringField("First Name")
    lname = StringField("Last Name")
    image = FileField("Image")
    ufname = StringField("First Name")
    ulname = StringField("Last Name")
    pronouns = SelectField(choices=[('---','---'),('He/Him', 'He/Him'),('She/Her','She/Her'),('They/Them','They/Them'),('Any/All','Any/All')])
    birthdate = DateField()
    personalemail = EmailField('Personal Email',validators=[(validators.Optional()),(Email())])
    mobile = IntegerField(validators=[(validators.Optional()),(NumberRange(min=1000000000, max=9999999999, message="Must be a 7 digit number with no space or other characters."))])
    ustreet = TextAreaField()
    ucity = StringField()
    ustate = StringField()
    uzipcode = IntegerField(validators=[(validators.Optional()),(NumberRange(min=10000, max=99999, message="Must be a 5 digit number."))])
    altphone = IntegerField(validators=[(validators.Optional()),(NumberRange(min=1000000000, max=9999999999, message="Must be a 7 digit number with no space or other characters."))])
    ugender = TextAreaField()
    uethnicity = MultiCheckboxField(choices=[("Decline to say","Decline to say"),('American Indian or Alaskan Native','American Indian or Alaskan Native'), ('Asian Indian','Asian Indian'), ('Black or African American','Black or African American'), ('Cambodian','Cambodian'), ('Chinese','Chinese'), ('Filipino','Filipino'), ('Guamanian','Guamanian'), ('Hawaiian','Hawaiian'), ('Hispanic or Latino','Hispanic or Latino'), ('Hmong','Hmong'), ('Japanese','Japanese'), ('Korean','Korean'), ('Laotian','Laotian'), ('Samoan','Samoan'), ('Vietnamese','Vietnamese'), ('White','White')])
    uethnicityother = TextAreaField()
    submit = SubmitField("Submit")

class AdultForm(FlaskForm):
    fname = StringField()
    lname = StringField()
    relation = StringField()
    mobile = IntegerField(validators=[(validators.Optional()),(NumberRange(min=1000000000, max=9999999999, message="Must be a 7 digit number with no space or other characters."))])
    altphone = IntegerField(validators=[(validators.Optional()),(NumberRange(min=1000000000, max=9999999999, message="Must be a 7 digit number with no space or other characters."))])
    email = EmailField(validators=[(validators.Optional()),(Email())])
    altemail = EmailField(validators=[(validators.Optional()),(Email())])
    street = TextAreaField()
    city = StringField()
    state = StringField()
    zipcode = IntegerField(validators=[(validators.Optional()),(NumberRange(min=10000, max=99999, message="Must be a 5 digit number."))])
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