import logging,asyncio,aiomysql
class Model(dict,metaclass=ModelMetaClass):
    pass
class ModelMetaClass(type):
    def __new__(cls, name,bases,attrs):
        if name=='Model':
            return type.__new__(cls,name,bases,attrs)
        tableName = attrs.get('table',None) or name
        logging.info('from model:%s(table %s)',name,tableName)
        mapping = dict()
        fields = []
        key = None
        for k,v in attrs.items:
            if isinstance(v,Field):
                logging.info('founding mapping %s->%s',(k,v))
                mapping[k] = v
                if v.key:
                    if key:
                        raise BaseException('Duplicate primary key for field: %s' % k)
                    key = v.key
                else:
                    fields.append(k)
        if not key:
            raise BaseException('Primary key not found')
        for k in mapping.keys():
            attrs.pop(k)
        escapedFields = list(map(lambda f:'`%s`' % f,fields))
        attrs['mapping'] = mapping
        attrs['table'] = tableName
        attrs['key'] = key
        attrs['fields'] = fields
        attrs['select'] = 'select %s,%s from %s' %(key,','.join(escapedFields),tableName)
        attrs['insert'] = 'insert'
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
