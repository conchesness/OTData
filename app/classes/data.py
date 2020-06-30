
from mongoengine import EmbeddedDocumentListField, Document, ObjectIdField, EmailField, BooleanField, URLField, DateField, FileField, StringField, IntField, ReferenceField, EmbeddedDocument, DateTimeField, ListField, CASCADE
from bson.objectid import ObjectId
import datetime as d

class Adult(EmbeddedDocument):
    oid = ObjectIdField(sparse=True, required=True, default=ObjectId(), unique=True, primary_key=True)
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

class Enrollment(EmbeddedDocument):
    oid = ObjectIdField(sparse=True, required=True, default=ObjectId(), unique=True, primary_key=True)
    section = ReferenceField('Section')
    mp1 = StringField()
    mp2 = StringField()
    mp3 = StringField()
    mp4 = StringField()
    mp5 = StringField()
    mp6 = StringField()
    mp7 = StringField()
    mp8 = StringField()
    notes = ListField(StringField())

class Communication(EmbeddedDocument):
    oid = ObjectIdField(sparse=True, required=True, default=ObjectId(), unique=True, primary_key=True)
    date = DateTimeField(default=d.datetime.utcnow)
    type_ = StringField() # sms, email
    to = StringField() # email addresses or phone num
    fromadd = StringField() # email address or phone num
    fromwho = ReferenceField('User')
    subject = StringField()
    body = StringField()

class Note(EmbeddedDocument):
    oid = ObjectIdField(sparse=True, required=True, default=ObjectId(), unique=True, primary_key=True)
    type_ = StringField() # Note, Mtg, Call
    date = DateTimeField()
    author = ReferenceField('User')
    content = StringField()

class User(Document):
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
    otemail = StringField(unique=True, required=True)
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
    
    # Data that can be edited
    isadmin = BooleanField(default=False)
    pronouns = StringField()
    ufname = StringField()
    ulname = StringField()
    image = FileField()
    birthdate = DateField()
    personalemail = StringField()
    mobile = IntField()
    ustreet = StringField()
    ucity = StringField()
    ustate = StringField()
    uzipcode = IntField()
    altphone = IntField()
    ugender = StringField()
    uethnicity = ListField(StringField())
    uethnicityother = StringField()
    
    # If this is a teacher
    tnum = IntField()
    troom = StringField()
    tdept = StringField()
    taeriesname = StringField()
    trmphone = StringField()

    # Related Data
    sections = ListField(ReferenceField('Section')) # Both Teacher Section and Student sections
    adults = EmbeddedDocumentListField('Adult')
    enrollments = EmbeddedDocumentListField('Enrollment')
    communications = EmbeddedDocumentListField('Communication')
    notes = EmbeddedDocumentListField('Note')
    interventions = ListField(ReferenceField('Intervention'))
    checkins = ListField(ReferenceField('Checkin'))

    meta = {
        'ordering': ['+glname', '+gfname']
    }

class Course(Document):
    num = StringField()
    name = StringField()
    dept = StringField()
    sections = ListField(ReferenceField('Section')) 

class Section(Document):
    num = IntField()
    course = ReferenceField('Course')
    coursenum = StringField()
    coursename = StringField()
    teacher = ReferenceField('User')
    room = StringField()
    per = IntField()
    students = ListField(ReferenceField('User'))

class Intervention(Document):
    owner = ReferenceField('User')
    student = ReferenceField('User')
    start = DateField()
    end = DateField()
    goal = StringField()
    notes = StringField()

class Checkin(Document):
    created = DateTimeField()
    student = ReferenceField('User')
    scale = IntField()
    comment = StringField()
    ip = StringField()
    location = StringField()

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