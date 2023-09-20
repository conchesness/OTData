
#from typing_extensions import Required
from ast import List
from mongoengine import Document, EmbeddedDocumentListField, DictField, FloatField, ObjectIdField, EmailField, BooleanField, URLField, DateField, FileField, StringField, IntField, ReferenceField, EmbeddedDocument, DateTimeField, ListField, CASCADE
#from flask_mongoengine import Document
from bson.objectid import ObjectId
import datetime as d

class Adult(EmbeddedDocument):
    preferredcontact = BooleanField()
    oid = ObjectIdField(default=ObjectId(), sparse=True, required=True, unique=True, primary_key=True)
    fname = StringField()
    lname = StringField()
    mobile = IntField()
    altphone = IntField()
    email = StringField()
    altemail = StringField()
    street = StringField()
    city = StringField()
    state = StringField()
    zipcode = IntField()
    relation = StringField() # Adult, Mother, Father, Grandmother...
    notes = StringField()
    primarylang = StringField()
    needstranslation = BooleanField()

class Communication(EmbeddedDocument): # Embedded on User Document
    oid = ObjectIdField(sparse=True, required=True, default=ObjectId(), unique=True, primary_key=True)
    date = DateTimeField(default=d.datetime.utcnow)
    confidential = BooleanField(default=True)
    type_ = StringField() # sms, email
    to = StringField() # email addresses or phone num
    fromadd = StringField() # email address or phone num
    fromwho = ReferenceField('User')
    subject = StringField()
    body = StringField()

    meta = {
        'ordering': ['date']
    }

class Message(Document):
    student = ReferenceField('User')
    twilioid = StringField(sparse=True, unique=True)
    to = StringField()
    #TODO: from field should be a user object, not a name
    from_ = StringField()
    from_user = ReferenceField('User')
    reply_to = ReferenceField('User') 
    body = StringField()
    datetimesent = DateTimeField()
    status = StringField()
    direction = StringField()
    media = StringField()

    meta = {
        'ordering': ['-datetimesent']
    }

class Note(EmbeddedDocument): #Embedded on User Document
    oid = ObjectIdField(default=ObjectId(), sparse=True, required=True, unique=True, primary_key=True)
    type_ = StringField() # Note, Mtg, Call
    date = DateField()
    author = ReferenceField('User')
    content = StringField()

    meta = {
        'ordering': ['date']
    }

# TODO CheckIns should reference a GoogleClassroom document
# instead of storing the id and name of the class
class CheckIn(Document):
    createdate = DateTimeField(default=d.datetime.utcnow)
    gclassid = StringField()
    googleclass = ReferenceField('GoogleClassroom')
    gclassname = StringField()
    student = ReferenceField('User')
    user_agent = StringField()
    locationData = DictField()
    workingon = StringField()
    desc = StringField()
    status = StringField(default='inactive')
    synchronous = BooleanField()
    createdBy = ReferenceField('User') # Only present if not created by student
    approved = BooleanField()

    
    cameraoff = BooleanField()
    cameraoffreason = StringField()
    cameraoffreasonother = StringField()

    meta = {
        'ordering': ['-createdate']
    }


class PostGrad(EmbeddedDocument):
    oid = ObjectIdField(default=ObjectId(), sparse=True, required=True, unique=True, primary_key=True)
    type_ = StringField()
    org = StringField()
    link = StringField()
    major = StringField()
    graduated = BooleanField()
    desc = StringField()
    yr_started = IntField()
    yr_ended = IntField()
    pg_st_address = StringField()
    pg_city = StringField()
    pg_state = StringField()
    pg_zip = IntField()

class ProjectTask(EmbeddedDocument):
    oid = ObjectIdField(default=ObjectId(), sparse=True, required=True, unique=True, primary_key=True)
    order = IntField()
    name = StringField()
    desc = StringField()
    status = StringField(default="New")
    completedate = DateTimeField()
    createdate = DateTimeField(default=d.datetime.utcnow)
    
    meta = {
        'ordering': ['order','createdate']
    }

class ProjectCheckin(EmbeddedDocument):
    oid = ObjectIdField(default=ObjectId(), sparse=True, required=True, unique=True, primary_key=True)
    workingon = ObjectIdField('ProjectTask')
    workingonname = StringField()
    status = StringField()
    desc = StringField()
    createdate = DateTimeField(default=d.datetime.utcnow)

    meta = {
        'ordering': ['-createdate']
    }

class Project(Document):
    name = StringField()
    student = ReferenceField('User')
    gclass = ReferenceField('GoogleClassroom')
    tasks = EmbeddedDocumentListField('ProjectTask')
    checkins = EmbeddedDocumentListField('ProjectCheckin')
    createdate = DateTimeField(default=d.datetime.utcnow)

    meta = {
        'ordering': ['-createdate']
    }

class User(UserMixin, Document):
    # temp
    # gclasses = StringField()
    # sections = StringField()
    # enrollments = StringField()
    # Immutable Data
    afname = StringField()
    alname = StringField()
    aadults = StringField()
    aadultemail = StringField()
    aadult1phone = StringField()
    aadult2phone = StringField()
    aethnicity = StringField()
    agender = StringField()
    grade = IntField()
    langflu = StringField()
    sped = StringField() 
    oemail = StringField(unique=True, required=True)
    aphone = StringField()
    aeriesid = IntField(sparse=True, unique=True, required=False)
    gid = StringField(sparse=True, unique=True, required=False)
    role = StringField()    # staff, teacher, student
    astreet = StringField()
    acity = StringField()
    astate = StringField()
    azipcode = IntField()
    gpa = IntField()
    cohort = StringField() #academy or house name
    gclassguardians = DictField(default={})
    gclassguardianinvites = DictField(default={})
    gprofile_pic = URLField()
    gname = StringField()
    
    # Data that can be edited
    lat = FloatField()
    lon = FloatField()
    fname = StringField(default=afname)
    lname = StringField(default=alname)
    isadmin = BooleanField(default=False)
    pronouns = StringField()
    ufname = StringField()
    ulname = StringField()
    image = FileField()
    birthdate = DateField()
    personalemail = StringField()
    altemail = EmailField()
    mobile = IntField()
    ustreet = StringField()
    ucity = StringField()
    ustate = StringField()
    uzipcode = IntField()
    altphone = IntField()
    ugender = StringField()
    uethnicity = ListField(StringField())
    uethnicityother = StringField()
    lastedited = ListField()
    lastlogin = DateTimeField()
    casemanager = StringField(required=False)
    linkedin = StringField()
    shirtsize = StringField(required=False)
    breakstart = DateTimeField()
    breakclass = StringField()
    breakduration = IntField()

    # Borrowed Computer
    compequiptype = StringField()
    compidnum = StringField()
    compstickernum = IntField()
    compdateout = DateField()
    compdatereturned = DateField()
    compstatus = StringField()
    compstatusdesc = StringField()
    
    # If this is a teacher
    tnum = IntField()
    troom = StringField()
    tdept = StringField()
    taeriesname = StringField()
    trmphone = StringField()

    # if this is a parent
    this_parents_students = ListField(ReferenceField('User'))
    this_students_parents = ListField(ReferenceField('User'))

    # Related Data
    adults = EmbeddedDocumentListField('Adult')
    communications = EmbeddedDocumentListField('Communication')
    notes = EmbeddedDocumentListField('Note')
    # interventions = ListField(ReferenceField('Intervention'))
    plan = ListField(ReferenceField('Plan'))
    # TODO make this two way
    checkins = ListField(ReferenceField('CheckIn'))
    postgrads = EmbeddedDocumentListField('PostGrad')

    meta = {
        'ordering': ['+glname', '+gfname']
    }

class Equipment(Document):
    type = StringField(required=True)
    location = StringField(required=True)
    uid = StringField(required=True, unique=True)
    stickernum = IntField()
    status = StringField(required=True)
    statusdesc = StringField()
    editdate = DateTimeField()

    meta = {
        'ordering': ['location','stickernum']
    }

class Help(Document):
    requester = ReferenceField('User')
    reqhelper = ReferenceField('User')
    status = StringField() # asked, offered, confirmed
    helper = ReferenceField('User')
    created = DateTimeField(default=d.datetime.utcnow)
    offered = DateTimeField()
    confirmed = DateTimeField()
    #helpdesc = StringField()
    gclass = ReferenceField('GoogleClassroom')
    confirmdesc = StringField()
    tokensAwarded = DateTimeField()
    note = StringField()

    meta = {
        'ordering': ['status','created']
    }

class Token(Document):
    owner = ReferenceField('User', required=True)
    giver = ReferenceField('User', required=True)
    transaction = DateTimeField(default=d.datetime.utcnow)
    amt = IntField(default=1)
    help = ReferenceField('Help')
    note = StringField()

class IdealOutcome(EmbeddedDocument):
    oid = ObjectIdField(default=ObjectId(), sparse=True, required=True, unique=True, primary_key=True)
    name = StringField()
    example = StringField()
    description = StringField()

class Theme(EmbeddedDocument):
    oid = ObjectIdField(default=ObjectId(), sparse=True, required=True, unique=True, primary_key=True)
    old = BooleanField()
    name = StringField()
    timeframe = StringField()
    description = StringField()
    idealoutcomes = EmbeddedDocumentListField('IdealOutcome')

class PlanSettings(Document):
    timeframe = StringField()
    yearbegin = DateField(unique=True)
    summerbegin = DateField(unique=True)
    seasonwinterbegin = DateField(unique=True)
    seasonspringbegin = DateField(unique=True)
    semestertwobegin = DateField(unique=True)

class Settings(Document):
    breakCanStart = DateTimeField()
    currClassEnd = DateTimeField()

class Intervention(EmbeddedDocument):
    status = StringField()
    statusother = StringField()
    type_ = StringField()
    description = StringField()

class Meeting(EmbeddedDocument):
    status = StringField()
    date = DateTimeField()
    notes = StringField()

class Plan(Document):
    student = ReferenceField('User',unique=True)
    themes = EmbeddedDocumentListField('Theme')
    interventions = EmbeddedDocumentListField('Intervention')
    meetings = EmbeddedDocumentListField('Meeting')

class PlanCheckin(Document):
    plan=ReferenceField('Plan')
    createdate = DateTimeField()
    todayfocus = ListField()
    yesterdayrating = IntField()
    yesterdaynarrative = StringField()
    todaynarrative = StringField()
    previousreference = ReferenceField('self')

# used in CourseCatalog
class Course(Document):
    aeriesnum = StringField(unique=True)
    aeriesname = StringField()
    level = StringField()
    name = StringField()
    dept = StringField()
    atog = StringField()
    yearinschool = StringField()
    pathway = StringField()

# used in CourseCatalog
class Section(Document):
    course = ReferenceField('Course')
    teacher = ReferenceField('User', unique_with='course')
    pers = ListField()
    url = URLField()
    desc = StringField()
    pathway = StringField()
    prereq = StringField()
    yearinschool = ListField(StringField()) #frosh, soph, jr, sr
    modified = DateTimeField()

    meta = {
        'ordering': ['teacher.alname','teacher.afname']
    }

class Comment(Document):
    content = StringField()
    owner = ReferenceField('User',reverse_delete_rule=CASCADE)
    comment = ReferenceField('self')

    meta = {
        'ordering': ['+createdate']
    }

class Feedback(Document): 
    author = ReferenceField('User',reverse_delete_rule=CASCADE)
    createdate = DateTimeField(default=d.datetime.utcnow)
    modifydate = DateTimeField()
    url = StringField()
    subject = StringField()
    body = StringField()
    status = StringField()
    priority = StringField()
    solution = StringField()

    meta = {
        'ordering': ['+status','+priority', '+createdate']
    }

class Post(Document):
    user = ReferenceField('User',reverse_delete_rule=CASCADE) 
    feedback = ReferenceField('Feedback')
    subject = StringField()
    body = StringField()
    createdate = DateTimeField(default=d.datetime.utcnow)
    modifydate = DateTimeField()

    meta = {
        'ordering': ['-createdate']
    }

class Event(Document):
    owner = ReferenceField('User')
    title = StringField()
    desc = StringField()
    #date = DateTimeField(format='%Y-%m-%d')
    date = DateTimeField()
    #job = ReferenceField('Job',reverse_delete_rule=CASCADE)

    meta = {
        'ordering': ['+date']
    }

class Config(Document):
    devenv = BooleanField()
    localtz = StringField()

class Group(Document):
    owner = ReferenceField('User')
    name = StringField()
    desc = StringField()
    students = ListField(ReferenceField('User'))
    
class StudentSubmission(Document):
    #student = ReferenceField('User', required=True)
    stugid = StringField(required=True)
    gclassroom = ReferenceField('GoogleClassroom', required=True)
    studsubid = StringField(unique=True, required=True)
    studsubdict = DictField(required=True)
    lastupdate = DateTimeField(required=True)

# a join table between GoogleClassroom and User
class GEnrollment(Document):
    gclassroom = ReferenceField('GoogleClassroom', required=True, sparse=True)
    owner = ReferenceField('User', unique_with='gclassroom', sparse=True, required=True)
    createdate = DateTimeField(default=d.datetime.utcnow)
    status = StringField(default='~~~') # Created by student active, inacative, ignore
    classnameByUser = StringField() # created by user for sorting
    nummissingupdate = DateTimeField()
    missingasses = DictField()
    missinglink = StringField()
    sortCohort = StringField(default='~')
    submissionsupdate = DateTimeField()

class Standard(Document):
    name = StringField(required=True)
    desc = StringField(required=True)
    gclass = ReferenceField('GoogleClassroom', required=True, unique_with='name')
    meta = {
        'ordering': ['+name']
    }

class CourseWork(Document):
    gclassroom = ReferenceField('GoogleClassroom', required=True)
    courseworkid = StringField(unique=True, sparse=True, required=True)
    courseworkdict = DictField()
    createdate = DateTimeField(default=d.datetime.utcnow)
    lastupdate = DateTimeField()
    standards = ListField(ReferenceField('Standard'))
    topic = StringField()

# courseworkdict values: https://developers.google.com/classroom/reference/rest/v1/courses.courseWork

class GoogleClassroom(Document):
    #temp
    # groster = StringField()
    ####
    teacher = ReferenceField('User')
    gteacherdict = DictField()
    gclassdict = DictField()
    courseworkdict = DictField()
    courseworkupdate = DateTimeField()
    # TODO move this to CourseWork class
    studsubsdict = DictField()
    gclassid = StringField(unique=True)
    teacher = ReferenceField('User')
    # This is a list of possible cohorts for this class
    sortcohorts = ListField()
    #This filed is used to iteratively build the roster from Google Classroom
    #It should be empty excetp during the process of retrieve=ing the roster
    #From Google Classroom
    grosterTemp = ListField(DictField())
    aeriesid = StringField()
    aeriesname = StringField()
    pers = ListField()

class ReqClass(Document):
    name = StringField()
    semester = StringField() #Fall, Spring
    
class Transcript(Document):
    transcriptDF = DictField()
    student = ReferenceField('User',unique=True)
