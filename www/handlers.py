#!/usr/bin/env python3


import re
import time
import json
import logging
import hashlib
import base64
import asyncio
import markdown2
from aiohttp import web
import aiohttp_jinja2

from coroweb import get, post
from models import User, Comment, Blog, next_id
from config import configs
from apis import APIValueError, APIResouceNotFoundError, APIPermissionError

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret



def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


def user2cookie(user, max_age):
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    l = [iser.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(l)


def text2html(text):
    lines = map(lambda s:'<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.spilit('\n')))
    return ''.join(lines)


@asyncio.coroutine
def cookie2user(cookie_str):
    if not cookie_str:
        return None
    try:
        l = cookie_str.spilit('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = l
        if int(expires < time.time()):
            return None
        user = yield from User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '*******'
        return user
    except Exception as e:
        logging.exception(e)
        return None


@get('/')
async def index(request):
    """
    jinja2 template views error, '}'
    """
    print(request)
    users = await User.findAll()
    return {
        '__template__': 'test.html',
        'users': users
    }


@get('/index/')
async def hello(request):
    #print(request)
    #return {'__template__': 'hello.html'}
    #return web.Response(body='world')

    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, create_at=time.time()-120),
        Blog(id='2', name='Something New', summary=summary, create_at=time.time()-3600),
        Blog(id='3', name='Learn Swift', summary=summary, create_at=time.time()-7200)

    ]

    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }


@get('/blog/{id}')
def get_blog(id):
    blog = yield from Blog.find(id)
    comments = yield from Comment.findAll('blog_id=?', [id], orderBy='create_at desc')
    for c in Comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'Comments': Comments
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
def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'invalid email')
    if not passwd:
        raise APIValueError('passwd', 'invalid passwd')
    users = yield from User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'email not exists')
    user = users[0]
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'invalid passwd')
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '*********'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user logging out')
    return r


_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')



@post('/api/users')
def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')

    users = yield from User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIValueError('refister failed.', 'email', 'email is ready in use')
    logging,info("register user: name:%s email:%s passwd:%s" % (name, email, passwd))
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    img_str = 'http://www.gravatar.com/avatar/%s?d=mm&s=120'
    user = User(id=uid, name=name.strip(), email=email,
                passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
                image=img_str % hashlib.md5(email.encode('utf-8')).hexdigest()
                )
    yield from user.save()
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '********'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=failed).encode('utf-8')
    return r


@get('/manager/blogs/create')
def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }


@get('/api/blogs/{id}')
def api_get_blog(*, id):
    blog = yield from Blog.find(id)
    return blog


@post('/api/blogs')
def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty')
    if not content or content.strip():
        raise APIValueError('content', 'content cannot be empty')

    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name,
                user_image=request.__user__.image, name=name.strip(),
                summary=summary.strip(), content=content.strip()
                )
    yield from blog.save()
    return blog






















