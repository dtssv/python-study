import logging
class Model(dict,metaclass=ModelMetaClass):
    def __init__(self,**kw):
        super(Model,self).__init__(**kw)
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(r'Model object hash no key:%s' % item)
class ModelMetaClass(type):
    def __new__(cls, name,bases,attrs):
        if name=='Model':
            return type.__new__(cls,name,bases,attrs)
        tableName = attrs.get('table',None) or name
        logging.info('from model:%s(table %s)',name,tableName)
        mapping = dict()
        fields = []
        key = None
        for k,v in attrs.items():
            if isinstance(v,Field):
                logging.info('founding mapping %s:%s' %(k,v))
                mapping[k] = v
                if v.key:
                    if key:
                        raise BaseException('Duplicate primary key for field: %s' % k)
                    key = k
                else:
                    fields.append(k)
        if not key:
            raise BaseException('Primary key not found')
        for k in mapping.keys():
            attrs.pop(k)
        escapeFields = list(map(lambda f:'`%s`' % f,fields))
        attrs['mapping'] = mapping
        attrs['fields'] = fields
        attrs['key'] = key
        attrs['tableName'] = tableName
        attrs['select'] = 'select %s,%s from %s' %(key,', '.join(fields),tableName)
        attrs['insert'] = 'insert into %s (%s,%s) values (%s)' %(tableName,key, ', '.join(escapeFields),createArgsString(len(escapeFields)+1))
        attrs['update'] = 'update %s set %s where %s=?' %(tableName,', '.join(map(lambda f:'`%s`=?' % mapping.get(f).name or f,fields)),key)
        attrs['delete'] = 'delete from %s where %s=?' %(tableName,key)
        return type.__new__(cls,name,bases,attrs)
def createArgsString(n):
    array = []
    for i in range(n):
        array.append('?')
    return ', '.join(array)
class Field(object):
    def __init__(self,name,type,key,default):
        self.name = name
        self.type = type
        self.key = key
        self.default = default
    def __str__(self):
        return '<%s,%s:%s>' %(self.__class__.__name__,self.name,self.type)
class StringField(Field):
    def __init__(self,name=None,type='varchar(100)',key=False,default=None):
        super.__init__(name,type,key,default)
class BooleanField(Field):
    def __init__(self,name=None,default=False):
        super.__init__(name,'boolean',False,default)
class IntegerField(Field):
    def __init__(self,name=None,type='int(10)',key=False,default=0):
        super.__init__(name,type,key,default)
class DoubleField(Field):
    def __init__(self,name=None,type='decimal(15,4)',key=False,default=0.0):
        super.__init__(name,type,key,default)
class TextField(Field):
    def __init__(self,name=None,type='text(100)',key=False,deault=None):
        super.__init__(name,type,key,deault)
