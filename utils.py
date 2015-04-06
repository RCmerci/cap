import re

class FormatReUrl(object):
    ### [url] is regex , [prefix] is normal string.
    def __init__(self, url):
        self.init_url = url
        self.formated_url = self.format_url(url)

    def format_url(self, url):
        ### /aaa/bbb
        ### /aaa
        ### /
        _url = url.strip()
        if _url == "":
            return "/"
        _url = _url.strip("/")
        # return "/" + re.sub(r"\\\\[AbBdDsSwWZ]","", _url.encode("string-escape"))
        return "/" + _url

    def consume_prefix(self, prefix=None):
        if prefix:
            _prefix = self._format_prefix(prefix)
            _count = _prefix.count("/")
            _index = 0
            for i in range(_count+1):
                _index = self.formated_url.find("/", _index) + 1
            _index -= 1
            _prefix_regex = self.formated_url[:_index]
            matched_prefix = re.match(_prefix_regex, _prefix)
            if not matched_prefix:
                return self

            return FormatReUrl(self.formated_url[_index:])
        else:
            ### if not given `prefix`, then remove the `/XXX` in  `/XXX/yyy/zzz`
            ### return FormatReUrl("/yyy/zzz")
            ### or "/" -> "/"
            index = self.formated_url.find('/', 1)
            if index == -1:
                return self
            return FormatReUrl(self.formated_url[index:])

    def _format_prefix(self, prefix):
        _prefix = prefix.strip(" /")
        if _prefix == "":
            return ""
        _prefix = "/" + _prefix.strip("/")
        return _prefix

    @property
    def url(self):
        return self.formated_url

    def __str__(self):
        return self.formated_url

class FormatUrl(FormatReUrl):
    ### [url] is normal string, [prefix] is regex.
    
    def format_url(self, url):
        if isinstance(url, FormatReUrl):
            return url.url
        _url = url.strip()
        if _url == "":
            return "/"
        _url = _url.strip("/")
        return "/" + _url

    def consume_prefix(self, prefix=None):
        if prefix<>None:
            _prefix = self._format_prefix(prefix)
            filter_func = lambda x: bool(len(x))
            _prefix_l = filter(filter_func, _prefix.split("/"))
            _url_l = filter(filter_func, self.formated_url.split("/"))
            _part_url_l = _url_l[:len(_prefix_l)]
            for reg, url in zip(_prefix_l, _url_l):
                matched = re.match(reg, url)
                if not matched:
                    return self
            res = "/".join(_url_l[len(_prefix_l):])
            return FormatUrl(res)
            # matched = re.match(_prefix, self.formated_url)
            # if not matched:
            #     return self
            # assert(self.formated_url.startswith(matched.group()))
            # return FormatReUrl(self.formated_url[len(matched.group()):])
        else:
            index = self.formated_url.find('/', 1)
            if index == -1:
                return self
            return FormatReUrl(self.formated_url[index:])

    def _format_prefix(self, prefix):
        _prefix = prefix.strip(" /")
        if _prefix == "":
            return ""
        _prefix = "/" + _prefix.strip("/")
        # return re.sub(r"\\\\[AbBdDsSwWZ]","", _prefix.encode("string-escape"))
        return _prefix

class FormatRePrefix(object):
    def __init__(self, prefix):
        self.init_prefix = prefix
        self.formated_prefix = self.format_prefix(self.init_prefix)

    def format_prefix(self, origin):
        _prefix = origin.strip(" /")
        if _prefix == "":
            return ""
        _prefix = "/" + _prefix.strip("/")
        return _prefix
    
    @property
    def val(self):
        return self.formated_prefix

    def __str__(self):
        return self.formated_prefix
    
if __name__ == "__main__":
    import pdb
    ### test here
    a = FormatReUrl(r"")
    b = FormatReUrl(r"/")
    c = FormatReUrl(r"/aaa/bb/")
    d = FormatReUrl(r"aaa/bb")
    e = FormatReUrl(r"/.../bb/ccc/")
    
    assert(FormatReUrl(r"").url == r"/")
    assert(FormatReUrl(r"/").url == r"/")
    assert(FormatReUrl(r"/aaa/bb/").url == r"/aaa/bb")
    assert(FormatReUrl(r"aaa/bb").url == r"/aaa/bb")
    
    assert(a.consume_prefix(r"").url == r"/")
    assert(a.consume_prefix(r"aa").url == r"/")
    assert(b.consume_prefix(r"").url == r"/")
    assert(b.consume_prefix(r"/").url == r"/")
    assert(c.consume_prefix(r"aaa").url == r"/bb")
    assert(c.consume_prefix(r"/aaa").url == r"/bb")
    assert(c.consume_prefix(r"- -").url == r"/aaa/bb")
    assert(d.consume_prefix(r"aaa").url == r"/bb")
    assert(d.consume_prefix(r"/aaa").url == r"/bb")
    assert(d.consume_prefix(r"bbb").url == r"/aaa/bb")
    assert(d.consume_prefix(r"- -").url == r"/aaa/bb")
    assert(e.consume_prefix(r"/aaa").url == r"/bb/ccc")
    assert(e.consume_prefix(r"/aaa/bb").url == r"/ccc")

    
    aa = FormatUrl("")
    bb = FormatUrl("/")
    cc = FormatUrl("/aaa/bb/")
    dd = FormatUrl("aaa/bb")
    ee = FormatUrl("/.a./bb/ccc/")
    ff = FormatUrl("\\aa/bb/cc-")
    gg = FormatUrl("\a/b/c")
    assert(aa.url == "/")
    assert(bb.url == "/")
    assert(cc.url == "/aaa/bb")
    assert(dd.url == "/aaa/bb")
    assert(ee.url == "/.a./bb/ccc")
    assert(ff.url == "/\\aa/bb/cc-")
    assert(gg.url == "/\a/b/c")
    
    assert(aa.consume_prefix(r"/...").url == r"/")
    assert(bb.consume_prefix(r"/.").url == r"/")
    assert(cc.consume_prefix(r"a.+").url == r"/bb")
    assert(cc.consume_prefix(r"/.+/b.").url == r"/")
    assert(cc.consume_prefix(r".*/.*").url == r"/")
    assert(dd.consume_prefix(r"aas").url == r"/aaa/bb")
    assert(ee.consume_prefix(r"/.{3}").url == r"/bb/ccc")
    assert(ee.consume_prefix(r"/...").url == r"/bb/ccc")
    assert(ee.consume_prefix(r"/.\w.").url == r"/bb/ccc")
    assert(ee.consume_prefix(r"/...").url == r"/bb/ccc")
    assert(ee.consume_prefix(r"\w\w\w").url == r"/.a./bb/ccc")
    assert(ff.consume_prefix(r"\\aa/bb").url == r"/cc-")
    assert(gg.consume_prefix(r"\a").url == r"/b/c")
    print r"test success"
    pass


###########################################################################

status_dict = {
    100: "Continue",
    101: "Switching Protocols",
    102: "Processing",

    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    207: "Multi-Status",
    208: "Already Reported",
    226: "IM Used",

    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    306: "Switch Proxy",
    307: "Temporary Redirect",
    308: "Permanent Redirect",

    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Request Entity Too Large",
    414: "Request-URI Too Long",
    415: "Unsupported Media Type",
    416: "Requested Range Not Satisfiable",
    417: "Expectation Failed",
    418: "I'm a teapot",
    422: "Unprocessable Entity",
    423: "Locked",
    424: "Failed Dependency",
    426: "Upgrade Required",
    428: "Precondition Required",
    429: "Too Many Requests",
    431: "Request Header Fields Too Large",

    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    505: "HTTP Version Not Supported",
    506: "Variant Also Negotiates",
    507: "Insufficient Storage",
    508: "Loop Detected",
    510: "Not Extended",
    511: "Network Authentication Required",
    
    
}
