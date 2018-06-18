from www.orm import *
import time,uuid
def nextId():
    return '%015d%s000' %(int(time.time()*1000),uuid.uuid4().hex)
class User(Model):
    __table__ = 'User'
    id = StringField(key=True,type='varchar(50)',default=nextId)
