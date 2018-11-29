import  re,time,json,logging,hashlib,base64,asyncio
from www.coroweb import get,post
from www.models import User,Blog,Comment,nextId
from www.apis import *
from aiohttp import web
from www.markdown2 import *

COOKIE_NAME = 'webapp'
_COOKIE_KEY = 'Webapp'


def checkAdmin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


def getPageIndex(pageStr):
    p = 1
    try:
        p = int(pageStr)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

def text2Html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)


def user2Cookie(user, maxAge):
    '''
    Generate cookie str by user
    '''
    expires = str(int(time.time() + maxAge))
    s = '%s-%s-%s-%s' %(user.id, user.password, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


@asyncio.coroutine
def cookie2User(cookieStr):
    '''
    Parse cookie and load user if cookie is valid.
    '''
    if not cookieStr:
        return None
    try:
        L = cookieStr.split('-')
        if len(L) != 3:
            return None
        uid, expiress, sha1 = L
        if int(expiress) < time.time():
            return None
        user = yield from User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' %(uid, user.password, expiress, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.password = '******'
    except Exception as e:
        logging.exception(e)
        return None


@get('/')
def index(request):
    summary = 'Lorem ipsum dilor sit amet,consectetur adipsicing elit,sed do eiusmod ' \
              'tempor incididunt ut labore et dolore magna aliqua'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, createTime=time.time()-120),
        Blog(id='2', name='Something New', summary=summary, createTime=time.time()-3600),
        Blog(id='3', name='Learn Python', summary=summary, createTime=time.time()-7200)
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }


@get('/blog/{id}')
async def getBlog(id):
    blog = await Blog.find(id)
    comments = await Comment.findAll('blog_id=?', [id], orderBy='create_time desc')
    for c in comments:
        c.htmlContent = text2Html(c.content)
    blog.htmlContent = markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }


@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }


@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }


@post('/api/authenticate')
@asyncio.coroutine
def authenticate(*, email, password):
    if not email:
        raise APIValueError('email', 'Invalid email')
    if not password:
        raise APIValueError('password', 'Invalid password')
    users = yield from User.findAll('email=?', email)
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist')
    user = users[0]
    sha1 = hashlib.sha1
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(password.encode('utf-8'))
    if user.password != sha1.hexdigest():
        raise APIValueError('password', 'Invalid password')
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2Cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '******'
    r.content_type='application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out')
    return r


@get('/manage/blogs/create')
def manageCreateBlog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }


_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')


@post('/api/users')
@asyncio.coroutine
def registerUser(*, email, name, password):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not password or not password.strip():
        raise APIValueError('password')
    users = yield from User.findAll('email=?', email)
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    uid = nextId()
    sha1Password = '%s:%s' % (uid,password)
    sha1 = hashlib.sha1(sha1Password.encode('utf-8')).hexdigest()
    user = User(id=uid, name=name.strip(), email=email, password=sha1, image='https://timgsa.baidu.com/timg?image&quality=80&size=b9999_10000&sec=1542105917178&di=d1f6b6a11859ff9a2436460ed3c691dd&imgtype=0&src=http%3A%2F%2Fimgsrc.baidu.com%2Fimgad%2Fpic%2Fitem%2Fbba1cd11728b47104c5c00e9c9cec3fdfc0323a0.jpg')
    yield from user.save()
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2Cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '******'
    r.content_type='application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@get('/api/blogs/{id}')
async def getBlog(id):
    blog = await Blog.find(id)
    return blog


@get('/api/blogs')
async def apiCreateBlog(request, *, name, summary, content):
    checkAdmin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty')
    blog = Blog(userId=request.__user__.id, userName=request.__user__.name, userImage=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
    await blog.save()
    return blog

