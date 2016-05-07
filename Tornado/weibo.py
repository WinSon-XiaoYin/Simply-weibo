# -*- coding: utf-8 -*-

import tornado.web
import tornado.httpserver
import tornado.options
import tornado.ioloop
import os
from settings import db
import re

from tornado.options import options, define

define("port", default=8000, type=int)

def get_tags(content):
    r =re.compile(ur"@([\u4E00-\u9FA5\w-]+)")
    return r.findall(content)

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")

class WeiboHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("weibo_add.html")


class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = self.get_current_user()
        users = []
        followed_users = db.follow.find({"user": user})
        for followed_user in followed_users:
            user = followed_user["follow_user"]
            users.append(user)
        contents = db.weibo_content.find({"user":  {"$in": users}})
        self.render("index.html", weibo_contents=contents)

    @tornado.web.authenticated
    def post(self):
        user = self.get_current_user()
        users = []
        content = self.get_argument("content")
        db.weibo_content.insert({"content":content, "user": user})

        followed_users = db.follow.find({"user": user})
        for followed_user in followed_users:
            user = followed_user["follow_user"]
            users.append(user)
        contents = db.weibo_content.find({"user":  {"$in": users}})
        self.render("index.html", weibo_contents=contents)


class RegisterHandler(BaseHandler):
    def get(self):
        self.render("register.html")

    def post(self):
        account = self.get_argument("account", "")
        password = self.get_argument("password", "")
        if account == "" or password == "":
            return self.write("账号或密码为空")

        if db.user.find({"account": account}).count() > 0:
            return self.write("用户名已存在")

        db.user.insert({"account": account, "password": password})
        self.set_secure_cookie("user", account)
        self.redirect("/user")

class UsersHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        followed_users = db.follow.find({"user": self.get_current_user()}, {"follow_user": 1})
        filter_users = [follow["follow_user"] for follow in followed_users]
        filter_users.append(self.get_current_user())
        users = db.user.find({"account": {"$nin": filter_users}})
        self.render("user_list.html", users=users)


class UserInfoHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = self.get_current_user()
        contents = db.weibo_content.find({"user": user})
        self.render("userinfo.html", user=user, contents=contents)

class FollowHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = self.get_argument("follow_user", None)

        if not user:
            return self.redirect("/users")

        db.follow.insert({"follow_user": user, "user": self.get_current_user()})
        return self.redirect("/followed")


class FollowedHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        follow_users = db.follow.find({"user": self.get_current_user()})
        self.render("follow_user_list.html", follow_users=follow_users)


class LoginHandler(BaseHandler):
    def get(self):
        self.render("login.html")

    def post(self):
        account = self.get_argument("account", "")
        password = self.get_argument("password", "")

        if account == "" or password == "":
            return self.write("账号或密码为空")

        user = db.user.find_one({"account": account}, {"account":1, "password":1})

        if not user:
            return self.write("账号不存在")

        if user['password'] != password:
            return self.write("密码错误")

        self.set_secure_cookie("user", user['account'])
        self.redirect("/user")


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', MainHandler),
            (r'/login', LoginHandler),
            (r'/user', UserInfoHandler),
            (r'/register', RegisterHandler),
            (r'/weibo/add', WeiboHandler),
            (r'/users', UsersHandler),
            (r'/follow', FollowHandler),
            (r'/followed', FollowedHandler),
        ]
        settings = dict(
            cookie_secret="61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTp1o/Vo=",
            login_url="/login",
            debug=True,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
        )
        super(Application, self).__init__(handlers, **settings)

if __name__ == "__main__":
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()