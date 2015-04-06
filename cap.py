# -*- coding: utf-8 -*-
from wsgiref.util import setup_testing_defaults
from wsgiref.simple_server import make_server

# # A relatively simple WSGI application. It's going to print out the
# # environment dictionary after being updated by setup_testing_defaults
# def simple_app(environ, start_response):
#     setup_testing_defaults(environ)

#     status = '200 OK'
#     headers = [('Content-type', 'text/plain')]

#     start_response(status, headers)

#     ret = ["%s: %s\n" % (key, value)
#            for key, value in environ.iteritems()]
#     return ret

# httpd = make_server('', 8080, simple_app)
# print "Serving on port 8080..."
# httpd.serve_forever()

import re
import warnings
import functools
import threading, thread
import cgi
import pdb
import cStringIO
import functools

############
from utils import FormatUrl, FormatReUrl, FormatRePrefix

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
        if is_debug:
            pdb.set_trace()
        request.current_app_url = request.current_app_url.consume_prefix(self.prefix)
        # request.current_app_url = self._consume_prefix(request.current_app_url)
        func, matched_group = self.route(request.current_app_url, request.method)

        if isinstance(func, Cap):
            return func(environ, start_response)
        
        response = func(*matched_group.groups())
        
        ### `response` must be instance of [Response]
        assert(isinstance(response, Response))

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

    # def _consume_prefix(self, url):
    #     _url = url.lstrip("/")
    #     _url = re.sub(self.prefix.strip("/"), "", _url)
    #     return "/" + _url.lstrip("/")

    @property
    def prefix(self):
        return self.router.prefix

    def subapp(self, subcap):
        self.cap_stack.push(subcap)
        ## add `/.*` to match __all__ possible case starting with this prefix.
        tmp_prefix = "^" + subcap.router.prefix + "/.*"
        self.router.add(tmp_prefix, subcap)

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

    # def _fix_prefix(self, prefix):
    #     return "/" + prefix.replace("\\", "\\\\").strip("/")
        
    def add(self, url, func, method="any"):
        method = "fallback" if method=="any" else method
        if not method in self.method_list + ["fallback"]:
            warnings.warn("[method] arg is illegal")
            method = "fallback"
        l = getattr(self, method)

        for (ind, (_url, _)) in enumerate(l): # if the same [url] has existed,
            if _url == url:                   # replace it with new [func]
                l[ind] = func                 # else append (url, func) to [l]
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
            ### assume users' input url can be raw string.
            _url = FormatReUrl(url).url
            self.add(_url, func, method)
            return func
        return aux

    def search(self, path, method):
        ### return corrsponding function and matched group (re)
        for pathregex, func in getattr(self, method.lower()):
            matched = re.match(pathregex, path)
            if matched:
                return func, matched
        for pathregex, func in getattr(self, "fallback"):
            matched = re.match(pathregex, path)
            if matched:
                return func, matched
        raise RuntimeError("no matched url-function for: %s"%request.path)
    
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
    key_val_l = filter(space_filter, string.spilt(delimiter))
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
        length = int(self.env.get("CONTENT_LENGTH", 0))
        if length and self.env.has_key("wsgi.input"):
            return self.env["wsgi.input"].read(length)
        return ""

    @EnvDict(keyname="cap.POST")
    def POST(self):
        env_args = {}
        env_keys = ("CONTENT_TYPE", "CONETNT_LENGTH", "REQUEST_METHOD")
        for k in env_keys:
            env_args[k] = self.environ.get(k, "")

        args = {}
        res = {}
        args["fp"] = self.body
        args["envrion"] = env_args
        args["keep_blank_values"] = True
        fs = cgi.FieldStorage(**args)
        for k in fs:
            res[k] = fs[k]
        return res

    @EnvDict(keyname="_cap.current_app_url", readonly=False)
    def current_app_url(self):
        return FormatUrl(self.path)
    
class Response(object):
    default_status = "200 OK"
    default_tp = "text/html; charset=UTF-8"
    
    # def __init__(self, status, body, tp=None):
    def __init__(self, **kwargs):
        self._body = None
        self._status = None
        
        self.body = kwargs.get("body", "")
        self.status = kwargs.get("status", self.default_status)
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
        self.add_header(self._content_type)
        self.add_header("Content-Length", self._content_length)
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

    class BodyWrapper(object):
        def __init__(self, str_body):
            self._len = len(str_body)
            self._body = cStringIO.StringIO(str_body)
        def seek(self, *args, **kwargs):
            return self._body.seek(*args, **kwargs)
        def read(self, *args, **kwargs):
            return self._body.read(*args, **kwargs)
        def __len__(self):
            return self._len
            
    @body.setter
    def body(self, val):
        if hasattr(val, "read") and hasattr(val, "__len__"):
            self._body = val
        elif isinstance(val, basestring):
            self._body = self.BodyWrapper(val)
        else:
            raise NotImplementedError

class MediaRespnse(Response):
    def __init__(self, retfile, **kwargs):
        tp = kwargs.get("tp", "application/octet-stream")
        init_dict = {
            "body": retfile,
            "tp": tp,
            "status": self.default_status
        }
        super(MediaRespnse, self).__init__(**init_dict)
        
    
class StaticFileResponse(Response):
    def __init__(self, retfile, **kwargs):
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


class CapStack(object):
    _router_app_pushed = False
    def __init__(self, is_root=False):
        self._stack = []
        self._router_app = None
        self.is_root = is_root

    def push(self, cap_ins):
        self._stack.append(cap_ins)
        if len(self._stack) > 1 and self.is_root:
            ### if length of cap_list(self._stack) > 1,
            ### we need to add a router cap instance to route `prefix` of each
            ### cap instance.
            # tmp_prefix = "^" + cap_ins.router.prefix.replace("\\", "\\\\").rstrip("/") + "/.*"
            if not (self._router_app or CapStack._router_app_pushed):
                CapStack._router_app_pushed = True # change flag value
                app_router = Router()
                # app_router.add(tmp_prefix, cap_ins)
                self._router_app = Cap(app_router)
                self._router_app.subapp(cap_ins)
                self._router_app.subapp(self._stack[0])
            else:
                self._router_app.subapp(cap_ins)
                # self._router_app.router.add(tmp_prefix, cap_ins)

                
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

is_debug = True

#############################################

def run(port, ip, debug=True):
    global is_debug
    is_debug = debug
    if cap_stack.has_router_app():
        app = cap_stack.router_app
    else:
        app = cap_stack[0]
    ip = ip if ip else ""
    port = int(port) if port else 8080
    httpd = make_server(ip, port, app)
    
    print "Serving on %s:%s"%(ip, str(port))

    httpd.serve_forever()
    
