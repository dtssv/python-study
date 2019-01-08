import aiomysql, logging, configparser, asyncio


@asyncio.coroutine
def createPool(loop):
    logging.info('create connection pool....')
    config = configparser.ConfigParser()
    config.read('./conf/application.ini')
    global __pool
    __pool = yield from aiomysql.create_pool(
        host=config.get('database', 'host'),
        port=config.getint('database', 'port'),
        user=config.get('database', 'user'),
        password=config.get('database', 'password'),
        db=config.get('database', 'database'),
        autocommit=config.getboolean('database', 'autocommit'),
        maxsize=10,
        minsize=1,
        loop=loop
    )


@asyncio.coroutine
def select(sql, args, size=None):
    logging.info('SQL:%s' % sql)
    global __pool
    with (yield from __pool) as conn:
        cur = yield from conn.cursor(aiomysql.DictCursor)
        yield from cur.execute(sql.replace('?','%s'),args or ())
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchall()
        yield from cur.close()
        return rs


@asyncio.coroutine
def execute(sql, args, autocommit=False):
    logging.info('SQL:%s' % sql)
    global __pool
    with (yield from __pool) as conn:
        if not autocommit:
            yield from conn.begin()
        try:
            cur = yield from conn.cursor(aiomysql.DictCursor)
            yield from cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount
            yield from cur.close()
            if not autocommit:
                yield from conn.commit()
        except BaseException as e:
            if not autocommit:
                yield from conn.rollback()
            raise
        return affected


class ModelMetaClass(type):
    def __new__(cls, name,bases,attrs):
        if name=='Model':
            return type.__new__(cls,name,bases,attrs)
        tableName = attrs.get('__table__',None) or name
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
        attrs['insert'] = 'insert into %s (%s,%s) values (%s)' %(tableName, ', '.join(escapeFields), key, createArgsString(len(escapeFields)+1))
        attrs['update'] = 'update %s set %s where %s=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mapping.get(f).name or f), fields)), key)
        attrs['delete'] = 'delete from %s where %s=?' % (tableName, key)
        return type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass=ModelMetaClass):
    def __init__(self, **kw):
        super(Model,self).__init__(**kw)

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(r'Model object hash no key:%s' % item)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self,key):
        return getattr(self, key, None)

    def getValueorDefault(self, key,):
        value = getattr(self, key, None)
        if value is None:
            field = self.mapping[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('useing default value %s,%s' %(key,str(value)))
                setattr(self,key,value)
        return value

    @classmethod
    @asyncio.coroutine
    def findAll(cls,where=None,args=None,**kw):
        'find objects by where clause'
        sql = [cls.select]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy',None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit',None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit,int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit,tuple) and len(limit)==2:
                sql.append('?,?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value %s' % str(limit))
        rs = yield from select(' '.join(sql),args)
        return [cls(**r) for r in rs]

    @classmethod
    @asyncio.coroutine
    def findNumber(cls,selectField,where=None,args=None):
        'find number by where clause'
        sql = ['select %s num from %s' %(selectField,cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = yield from select(' '.join(sql),args,1)
        if len(rs) == 0:
            return None
        return rs[0]['num']

    @classmethod
    @asyncio.coroutine
    def find(cls,key):
        'find by key'
        rs = yield from select('%s where %s=?' %(cls.select,cls.key),[key],1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    @asyncio.coroutine
    def save(self):
        args = list(map(self.getValueorDefault,self.fields))
        args.append(self.getValueorDefault(self.key))
        result = yield from execute(self.insert,args)
        if result!=1:
            logging.warn('failed to insert record')

    @asyncio.coroutine
    def merge(self):
        args = list(map(self.getValue,self.fields))
        args.append(self.getValue(self.key))
        result = yield from execute(self.update,args)
        if result!=1:
            logging.warn('failed to update record by key')

    @asyncio.coroutine
    def remove(self):
        args = [self.getValue(self.key)]
        result = yield from execute(self.delete,args)
        if result!=1:
            logging.warn('failed to delete by key')


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
        super().__init__(name,type,key,default)


class BooleanField(Field):
    def __init__(self,name=None,default=False):
        super().__init__(name,'boolean',False,default)


class IntegerField(Field):
    def __init__(self,name=None,type='int(10)',key=False,default=0):
        super().__init__(name,type,key,default)


class DoubleField(Field):
    def __init__(self,name=None,type='decimal(15,4)',key=False,default=0.0):
        super().__init__(name,type,key,default)


class TextField(Field):
    def __init__(self,name=None,type='text',key=False,default=None):
        super().__init__(name,type,key,default)


class FloatField(Field):
    def __init__(self,name=None,type='real',key=False,default=0.0):
        super().__init__(name,type,key,default)
