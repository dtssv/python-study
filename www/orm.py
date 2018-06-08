import aiomysql,logging,configparser,asyncio
@asyncio.coroutine
def createPool(loop):
    logging.info('create connection pool....')
    config = configparser.ConfigParser()
    config.read('../conf/application.ini')
    global _pool
    _pool = yield from aiomysql.create_pool(
        host = config.get('database','host'),
        port = config.get('database','port'),
        user = config.get('database','user'),
        password = config.get('database','password'),
        db = config.get('database','database'),
        autocommit = config.get('database','autocommit')
    )
@asyncio.coroutine
def select(sql,args,size=None):
    logging.info(sql,args)
    global _pool
    with (yield from _pool) as conn:
        cur = yield from conn.cursor(aiomysql.DictCursor)
        yield from cur.execute(sql.replace('?','%s'),args or ())
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchall()
        yield from cur.close()
        return rs
@asyncio.coroutine
def execute(sql,args,autocommit=True):
    logging.info(sql)
    with (yield from _pool) as conn:
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount
            yield from cur.close()
        except BaseException as e:
            raise
        return affected
def createArgsString(num):
    l = []
    for i in range(num):
        l.append('?')
    return ','.join(l)
