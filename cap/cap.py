# -*- coding: utf-8 -*-
from wsgiref.util import setup_testing_defaults
from wsgiref.simple_server import make_server

import re
import warnings
import functools
import threading, thread
import cgi
import pdb
import cStringIO
import functools
import os
import traceback
import sys

############
from utils import FormatUrl, FormatReUrl, FormatRePrefix, FileWrapper

class Cap(object):
    def __init__(self, router):
        self.router = router

        self.cap_stack = CapStack()

        # cap_stack.push(self)
        
    def __call__(self, environ, start_response):
        ## [cap] is a wsgi application.
        ## a wsgi application can be called ,so define `__call__`.
        global request
        request.init(environ)
        request.current_app_url = request.current_app_url.consume_prefix(self.prefix)
        try:
            func, matched_group = self.route(request.current_app_url, request.method)
        except RuntimeError:
            return self.do_response(start_response, ErrorResponse(404))

        if isinstance(func, Cap):
            return func(environ, start_response)
        # try:
        #     response = func(*matched_group.groups())
        # except:
        #     tmp_buff = cStringIO.StringIO()
        #     traceback.print_tb(sys.exc_info()[2], file=tmp_buff)
        #     response = ErrorResponse(500, body=tmp_buff)
        response = func(*matched_group.groups())
        ### `response` must be instance of [Response]
        assert(isinstance(response, Response))

        return self.do_response(start_response, response)

    def do_response(self, start_response, response):
        start_response(response.status, response.header)
        if request.method == "head":
            return []
        return [response.body]

    def route(self, path, method):
        ### [path] is url‘s `PATH_INFO`
        ### `http://www.example.com/wdd/w?e=3#www` -> `/wdd/w`
        ### `http://a.b.c` -> `/`
        ## return corresponding `function` and `matched group`
        return self.router.search(str(path), method)

    @property
    def prefix(self):
        return self.router.prefix

    def subapp(self, subcap):
        self.cap_stack.push(subcap)
        ## add `/.*` to match __all__ possible case starting with this prefix.
        #### tmp_prefix = "^" + subcap.router.prefix + "(?:/.)*" 《－我忘了 (?:/.)*这么写有什么企图。不是应该(?:/.*)吗，而且为什么加括号呢（也忘了）!!!!
        # tmp_prefix = "^" + subcap.prefix + "(?:/.*)" ＝ ＝这是上一行的10分钟后。。。我想起来了
        # tmp_prefix = "^" + subcap.prefix + "(?:/.)*" # `(?:/.)*` 这么写的原因是： 1.  /prefix/others/.. 这样的URL应该被匹配
        self.router.app_add(subcap.prefix, subcap)          # 2. /prefix 这样的URL也应该被匹配到。（因为一个capapp里可能有回调对应的url是“/”）
        pass                                         # 然而 ＝ ＝， 又过了10分钟，想了一下，prefix的格式化已经移到Router.app_add里去了。

    def __str__(self):
        return "Cap instance, prefix:%s" % self.prefix
    __repr__ = __str__
class Router(object):
    method_list = ["get", "post", "head", "other"]
    router_instances = []
    def __init__(self, prefix=""):
        
        self.router_instances.append(self) # add [self] to [router_instaces]
        
        self.prefix = FormatRePrefix(prefix).val
        self.fallback = []
        self.get = []
        self.post = []
        self.head = []
        self.other = [] ### other http `method`s

    def app_add(self, prefix, func, method="any"):
        """
        用来添加 cap app
        """
        tmp_prefix = "^" + prefix + "(?:/.)*"
        self._add(tmp_prefix, func, method)
    def add(self, url, func, method="any"):
        """
        只用于添加 回调函数， 添加app用楼上的app_add.
        """
        _url = "(?:%s)$"%FormatReUrl(url).url
        self._add(_url, func, method)
    def _add(self, url, func, method="any"):
        """
        区别于 self.add,
        这个函数只用于内部，并假设 ［url］参数已标准化。
        """
        method = "fallback" if method=="any" else method
        if not method in self.method_list + ["fallback"]:
            warnings.warn("[method] arg is illegal")
            method = "fallback"
        l = getattr(self, method)
        for (ind, (_url, _)) in enumerate(l): # if the same [url] has existed,
            if _url == url:                   # replace it with new [func]
                l[ind] = (url, func)                 # else append (url, func) to [l]
                return 
        l.append((url, func))

    def delete(self, url, method="any"):
        raise NotImplementedError("[delete] is not implemented")

    def clear(method="all"):
        if method == "all":
            for m in self.method_list + ["fallback"]:
                setattr(self, m, [])
        elif method == "any":
            self.fallback = []
        elif method in self.method_list:
            setattr(self, method, [])
        else:
            warnings.warn("[method] arg is illegal")

    def route(self, url, method="any"):
        def aux(func):
            ### assume users' input url is raw string.
            _url = "(?:%s)$"%FormatReUrl(url).url 
            self._add(_url, func, method)
            return func
        return aux

    def search(self, path, method):
        ### return corrsponding function and matched group (re)
        ### 逻辑如下：
        ### 1. 如果有符合的回调函数， 直接返回
        ### 2. 如果有符合的子Cap实例， 存入 [cap_res]，继续搜索
        ### 3. 如果没找到符合的， 有[cap_res] 则返回， 没有则raise 错误。
        ### 4. 就是这样！
        cap_res = None
        for pathregex, func in getattr(self, method.lower()):
            matched = re.match(pathregex, path)
            if matched and isinstance(func, Cap):
                cap_res = (func, matched)
                continue
            if matched:
                return func, matched
        for pathregex, func in getattr(self, "fallback"):
            matched = re.match(pathregex, path)
            if matched and isinstance(func, Cap) and not cap_res:
                cap_res = (func, matched)
                continue
            if matched:
                return func, matched
        if cap_res:
            return cap_res    
        raise RuntimeError("no matched url-function for: %s"%request.path)

    def __str__(self):
        return "Router instance, prefix:%s" % self.prefix
    __repr__ = __str__
    
class LocalProperty(object):
    def __init__(self):
        self.local = threading.local()
    def __get__(self, obj, cls):
        return self.local.val if hasattr(self.local, "val") else None
    def __set__(self, obj, val):
        self.local.val = val
        return val
    def __delete__(self, obj):
        del self.local.val

        
def str2dict(string, delimiter="&", key_val_delimiter="="):
    """
    trans string to dict, string like: `k1=v1&k2=v2&` => `{k1:v1, k2:v2}`
    """
    def space_filter(s):
        return s.strip()
    res_dict = {}
    key_val_l = filter(space_filter, string.split(delimiter))
    for kv in key_val_l:
        kv = map(space_filter, kv.split(key_val_delimiter))
        if len(kv) == 2:
            res_dict[kv[0]] = kv[1]
        elif len(kv) == 1:
            res_dict[kv[0]] = ""
        else:
            raise ValueError("unpack error in [str2dict]")

    return res_dict


class PathDict(object):         # !!!!!!!!!!!! TODO 
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            try:
                setattr(self, k, v)
            except TypeError, e:
                warnings.warn(e)
    def __str__(self):
        return 


class EnvDict(object):
    env_name = "env"
    
    def __init__(self, keyname, envname=None, readonly=True):
        self.envname = envname if envname else self.env_name
        self.keyname = keyname
        self.readonly = readonly
        self.func = None
        
    def __get__(self, obj, cls):
        if not getattr(obj, self.envname).has_key(self.keyname):
            getattr(obj, self.envname)[self.keyname] = self.func(obj)
        return getattr(obj, self.envname)[self.keyname]

    def __set__(self, obj, val):
        if self.readonly:
            raise AttributeError(self.keyname + " is `read only`")
        try:
            getattr(obj, self.envname)[self.keyname] = val
        except KeyError, e:
            raise KeyError(str(e) + "\tbut it should be impossible")
        
    def __delete__(self, obj):
        if self.readonly:
            raise AttributeError(self.keyname + " is `read only`")
        try:
            del getattr(obj, self.envname)[self.keyname]
        except KeyError:
            pass

    def __call__(self, func):
        self.func = func
        return self

            
class Request(object):
    env = LocalProperty()
    
    def __init__(self, env=None):
        _env = env if env else {}
        self.env = _env

    init = __init__
        
    @EnvDict(keyname="cap.scheme")
    def scheme(self):
        return self.env.get("wsgi.url_scheme", "http")

    @EnvDict(keyname="cap.method")
    def method(self):
        return self.env.get("REQUEST_METHOD", "GET")

    @EnvDict(keyname="cap.path")
    def path(self):
        return FormatUrl(self.env.get("PATH_INFO"))

    @EnvDict(keyname="cap.content_length")
    def content_length(self):
        length = self.env.get("CONTENT_LENGTH", "")
        return int(length if length else 0)
    
    # def full_path(self):
    #     return 
    @EnvDict(keyname="cap.query_string")
    def query_string(self):
        return self.env.get("QUERY_STRING", "")

    @EnvDict(keyname="cap.query")
    def query(self):
        return str2dict(self.query_string)

    GET = query

    @EnvDict(keyname="cap.body")
    def body(self):
        length = self.content_length
        if length and self.env.has_key("wsgi.input"):
            return self.env["wsgi.input"].read(length)
        return ""

    @EnvDict(keyname="cap.POST")
    def POST(self):
        def parse_header(header):
            if not header.has_key("content-disposition"):
                return {}
            content_disposition = str2dict(header["content-disposition"], delimiter=";")
            res = {}
            for k, v in content_disposition.items():
                if v <> "":
                    res[k] = v.strip("\"\'") if v[0]==v[-1] and v[0] in "\'\"" else v
            header.update(res)
            return header
        env_args = {}
        env_keys = ("CONTENT_TYPE", "CONTENT_LENGTH", "REQUEST_METHOD")
        for k in env_keys:
            if k == "CONTENT_LENGTH":
                env_args[k] = str(self.content_length)
                continue
            env_args[k] = self.env.get(k, "")

        args = {}
        res = {}
        args["fp"] = cStringIO.StringIO(self.body)
        args["environ"] = env_args
        args["keep_blank_values"] = True
        fs = cgi.FieldStorage(**args)
        fs = fs.list
        for k in fs:
            if k.filename:
                res[k.name] = FileWrapper(k.file, **parse_header(dict(k.headers)))
                continue
            res[k.name] = k.value
        return res

    @EnvDict(keyname="_cap.current_app_url", readonly=False)
    def current_app_url(self):
        return FormatUrl(self.path)

from utils import status_dict
    
class Response(object):
    default_status = "200"
    default_tp = "text/html; charset=UTF-8"
    
    # def __init__(self, status, body, tp=None):
    def __init__(self, **kwargs):
        self._body = None
        self._status = None
        
        self.body = kwargs.get("body", "")
        self.status = kwargs.get("status", self.default_status)
        self.status = str(self.status) + " " + status_dict.get(int(self.status), "")
        self.tp = kwargs.get("tp", self.default_tp)
        
        self._header = []
        
    @property
    def _content_length(self):
        return len(self._body)

    @property
    def _content_type(self):
        return ("Content-Type", self.tp)

    @property
    def header(self):
        return self._header

    def add_header(self, *args):
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            self._header.append(tuple(args[0]))
        elif len(args) == 2 and \
        isinstance(args[0], basestring) and \
        isinstance(args[1], basestring):
            self._header.append(args)
        else:
            warnings.warn("[add_header]:illegal parameters.")
            pass
            
    # @property
    # def status(self):
    #     return self.status

    @property
    def body(self):
        self._body.seek(0)
        return self._body.read(self._content_length)

    class StrBodyWrapper(object):
        def __init__(self, body):
            self._len = len(body)
            self._body = cStringIO.StringIO(body)
        def seek(self, *args, **kwargs):
            return self._body.seek(*args, **kwargs)
        def read(self, *args, **kwargs):
            return self._body.read(*args, **kwargs)
        def __len__(self):
            return self._len
    class FileBodyWrapper(object):
        def __init__(self, body):
            self._len = os.stat(body.name).st_size
            self._body = body
        def seek(self, *args, **kwargs):
            return self._body.seek(*args, **kwargs)
        def read(self, *args, **kwargs):
            return self._body.read(*args, **kwargs)
        def __len__(self):
            return self._len
        def __del__(self):
            self._body.close()
    @body.setter
    def body(self, val):
        if isinstance(val, file):
            self._body = self.FileBodyWrapper(val)
        elif hasattr(val, "read") and hasattr(val, "__len__") and hasattr(val, "seek"):
            self._body = val
        elif isinstance(val, basestring):
            self._body = self.StrBodyWrapper(val)
        elif isinstance(val, cStringIO.OutputType):
            self._body = self.StrBodyWrapper(val.getvalue())
        else:
            raise NotImplementedError

class MediaRespnse(Response):
    def __init__(self, retfile, **kwargs):
        if isinstance(retfile, basestring):
            retfile = open(retfile, "rb")
        tp = kwargs.get("tp", "application/octet-stream")
        init_dict = {
            "body": retfile,
            "tp": tp,
            "status": self.default_status
        }
        super(MediaRespnse, self).__init__(**init_dict)
        
    @property
    def header(self):
        self.add_header(self._content_type)
        self.add_header("Content-Length", self._content_length)
        return self._header

    
class StaticFileResponse(Response):
    def __init__(self, retfile, **kwargs):
        if isinstance(retfile, basestring):
            retfile = open(retfile, "rb")
        if kwargs.has_key("tp"):
            tp = kwargs["tp"]
        elif hasattr(retfile, "tp"):
            tp = retfile.tp()
        else:
            tp = "text/plain"
        init_dict = {
            "tp": tp,
            "body": retfile,
            "status": self.default_status
        }
        super(StaticFileResponse, self).__init__(**init_dict)

    @property
    def header(self):
        self.add_header(self._content_type)
        self.add_header("Content-Length", self._content_length)
        return self._header


class ErrorResponse(Response):
    def __init__(self, status, **kwargs):
        init_dict = {
            "status": status,
            "body": kwargs.get("body", str(status))
        }
        super(ErrorResponse, self).__init__(**init_dict)

class CapStack(object):
    _router_app_pushed = False
    def __init__(self, is_root=False):
        self._stack = []
        self._router_app = None
        self.is_root = is_root
        if self.is_root:
            self._build_root_app()

    def push(self, cap_ins):
        self._stack.append(cap_ins)
        if self.is_root:
            ### add [cap_ins] to [root_app]
            self._router_app.subapp(cap_ins)

    def _build_root_app(self):
        router = Router()
        self._router_app = Cap(router)
    
    def pop(self):
        raise NotImplementedError

    def has_router_app(self):
        return self._router_app <> None

    @property
    def router_app(self):
        return self._router_app

    def __getitem__(self, ind):
        return self._stack[ind]

    
def app_register(cap):
    ### register `cap` as toplevel app
    global cap_stack
    cap_stack.push(cap)
    
####################################
###########  globals ###############

request = Request()

cap_stack = CapStack(is_root=True)

root = cap_stack.router_app.router

is_debug = True

static_url = r"/static"

static_root = r"./static/"

local_dic = threading.local()

######################################
######### init #######################
def _register_static_app():
    static_router = Router(static_url)
    static_app = Cap(static_router)
    app_register(static_app)
    @static_router.route(r"(.*)")
    def static_func(path):
        path = path.strip(" /")
        if is_debug:
            print "query static file: %s, at static root: %s"%(path, static_root)
        try:
            return StaticFileResponse(os.path.join(static_root, path))
        except IOError:
            return ErrorResponse(404)

    
#############################################

def run(port, ip, debug=True):
    global is_debug
    is_debug = debug
    ### add static handler
    _register_static_app()
    if cap_stack.has_router_app():
        app = cap_stack.router_app
    else:
        app = cap_stack[0]
    ip = ip if ip else ""
    port = int(port) if port else 8080
    httpd = make_server(ip, port, app)
    
    print "Serving on %s:%s"%(ip, str(port))

    httpd.serve_forever()
    
def application(env, start_response):
    """
    used by released version.
    """
    return cap_stack.router_app(env, start_response)
