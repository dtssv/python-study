from www.orm import *
import time, uuid


def nextId():
    return '%015d%s000' %(int(time.time()*1000),uuid.uuid4().hex)


class User(Model):
    __table__ = 'User'
    id = StringField(key=True,type='varchar(50)',default=nextId)
    email = StringField(type='varchar(50)')
    password = StringField(type='varchar(32)')
    admin = BooleanField(default=False)
    name = StringField(type='varchar(10)')
    image = StringField(type='varchar(500)')
    createTime = FloatField(default=time.time())


class Blog(Model):
    __table__ = 'Blog'
    id = StringField(key=True,type='varchar(50)',default=nextId)
    userId = StringField(type='varchar(50)')
    userName = StringField(type='varchar(50)')
    userImage = StringField(type='varchar(500)')
    name = StringField(type='varchar(50)')
    summary = StringField(type='varchar(200)')
    content = TextField()
    createTime = FloatField(default=time.time())


class Comment(Model):
    __table__='Comment'
    id = StringField(key=True,type='varchar(50)',default=nextId)
    userId = StringField(type='varchar(50)')
    blogId = StringField(type='varchar(50)')
    userName = StringField(type='varchar(50)')
    userImage = StringField(type='varchar(500)')
    content = TextField()
    createTime = FloatField(default=time.time())
