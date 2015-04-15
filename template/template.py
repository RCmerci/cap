#coding:utf-8#
import re, os, copy
from cStringIO import StringIO


class Template(object):
    def __init__(self, path, **env):
        self._path = path
        if not os.path.exists(path):
            raise IOError(path + "not exists")
        self.htmlfile = open(path, "rb")
        self.env = env
    def render(self, **kwargs):
        if not hasattr(self, "htmlpage_cache"):
            self.htmlpage_cache = HtmlPage(origin=preparse(self.htmlfile), name=self._path, **self.env)
        return self.htmlpage_cache.result(**kwargs)

# def insert(html, to, part_name):
#     pass

# def end_insert():
#     pass

# def provide(part_name):
#     pass

# def append(string):             # unused
#     pass

class Appender(object):
    def __init__(self):
        self._content = []
    def __call__(self, string):
        self._content.append(str(string))
    def get_value(self):
        return "".join(self._content)

ParseError = -1
def _lookahead(n, stringio):
    res = {}
    now_pos = stringio.tell()
    res["data"] = stringio.read(n)
    res["newpos"] = stringio.tell()
    stringio.seek(now_pos)
    return res

class ParseError(Exception):
    pass

def preparse(html_iter):           # html_iter is StringIO instance
    state_dict = {
        "html": {
            "\"": "html",
            "\'": "html",
            "++>": "template",
            "<++": "html",
            "others": "html"
        },
        "template": {
            "\"": "dstring",
            "\'": "sstring",
            "++>": ParseError,
            "<++": "html",
            "others": "template"
        },
        "dstring": {
            "\"": "template",
            "\'": "dstring",
            "++>": "dstring",
            "<++": "dstring",
            "others": "dstring"
        },
        "sstring": {
            "\"": "sstring",
            "\'": "template",
            "++>": "sstring",
            "<++": "sstring",
            "others": "sstring"
        }
    }
    # these states are all in template part.
    _template_states = ("template", "sstring", "dstring") 
    current_state = "html"
    current_html = StringIO()
    current_template = StringIO()
    template_stack = []        
    while True:
        char = html_iter.read(1)
        if char == "":
            if current_html:
                template_stack.append(current_html)
            elif current_template:
                template_stack.append(current_template)
            break
        if char == "\"":        # "
            if current_state == "html":
                current_html.write(char)
            elif current_state in _template_states:
                current_template.write(char)
            current_state = state_dict[current_state][char]
        elif char == "\'":      # '
            if current_state == "html":
                current_html.write(char)
            current_state = state_dict[current_state][char]
        elif char == "+":
            la = _lookahead(2, html_iter)
            if la["data"] == "+>": # ++>
                html_iter.seek(la["newpos"])
                if current_state == "html":
                    template_stack.append(current_html)
                    current_html = StringIO()
                    current_template.write("++>")
                elif current_state == "template":
                    raise ParseError("TODO add position info here.")
                elif current_state in ("sstring", "dstring"):
                    current_template.write("++>")
                current_state = state_dict[current_state]["++>"]
            else:
                if current_state == "html":
                    current_html.write(char)
                elif current_state in _template_states:
                    current_template.write(char)
                else:
                    raise RuntimeError("impossible case")
        elif char == "<":                     # TODO html里有好多 <符号
            la = _lookahead(2, html_iter)     # 会lookahead好多次好慢啊。。
            if la["data"] == "++":            # 解决方案： 1. 改语法，不用 <++
                if current_state == "html":   # 2. 先判断 current_state 是不是 html
                    current_html.write(char)
                elif current_state == "template":
                    current_template.write("<++")
                    template_stack.append(current_template)
                    current_template = StringIO()
                    html_iter.seek(la["newpos"])
                elif current_state in ("sstring", "dstring"):
                    current_template.write("<++")
                    html_iter.seek(la["newpos"])
                else:
                    raise RuntimeError("impossible case")
                current_state = state_dict[current_state]["<++"]
            else:
                if current_state == "html":
                    current_html.write(char)
                elif current_state in _template_states:
                    current_template.write(char)
                else:
                    raise RuntimeError("impossible case")
        else:                   # `others` case
            if current_state == "html":
                current_html.write(char)
            elif current_state in _template_states:
                current_template.write(char)
            else:
                raise RuntimeError("impossible case")
    return template_stack




class HtmlPage(object):
    Instances = {}
    def __init__(self, name, origin, **kwargs):
        self.base = None
        self.sub = None         # 好像没有用
        self.origin = origin
        # self.ir = copy.copy(origin)
        self.insert_place = {}
        self.provide_place = []
        self.name = name
        HtmlPage.Instances.update({self.name: self}) # add self to class level val
        ######### init followed
        self.env = kwargs
        # self.scan()

    def render(self):           # 拼凑 html， 但不对 普通 语句求值
        self.res = []
        self.scan()
        if self.base:
            self.base.render()
            for stat in self.base.res:
                tp, string = self.identify(stat.getvalue())
                if tp == "insert":
                    raise RuntimeError(u"应该没有insert类型了呀")
                elif tp == "end_insert":
                    raise RuntimeError(u"应该没有end_insert类型了呀")
                elif tp == "provide":
                    provided_name = self._provided_name(string)
                    if self.insert_place.has_key(provided_name):
                        insert_pair = self.insert_place[provided_name]
                        self.res.extend(copy.copy(self.ir[insert_pair[0]+1 : insert_pair[1]]))
                elif tp == "normal":
                    # raise RuntimeError(u"应该没有normal类型了呀")
                    self.res.append(stat)
                else:           # html
                    self.res.append(stat)
        else:                   # no self.base
            self.res = copy.copy(self.ir)
        return self.res
    def result(self, **env):           # 对 普通 语句 求值
        self.env = env
        ires = []
        res = StringIO()
        if not hasattr(self, "res"):
            self.res = self.render()
        for stat in self.res:
            tp, string = self.identify(stat.getvalue())
            if tp == "normal":
                evalres = self.do_normal(string)
                ires.append(StringIO(evalres))
            else:
                ires.append(stat)
        for i in ires:
            res.write(i.getvalue())
        return res
    def scan(self):
        self.ir = copy.copy(self.origin)
        for index, stat in enumerate(self.ir):
            tp, string = self.identify(stat.getvalue())
            if tp == "insert":
                end_index = self._find_end_insert(index + 1)
                self.do_insert(string, index, end_index)
            elif tp == "end_insert":
                pass
            elif tp == "provide":
                self.do_provide(string, index)
            elif tp == "normal":                         # 对一般的模版的语句不应该
                # ret = self.do_normal(string)             # 在scan的时候执行，应该
                # self.ir[index] = cStringIO.StringIO(ret) # 在尽量晚的时候执行。
                # pass                                     # 比如 [self.result]里。
                pass                                      #所以这里只是不改变。
            else:               # html ,just keep
                pass
    def identify(self, string):
        if string.startswith("++>") and string.endswith("<++"):
            string = string[3:-3].strip()
            if string.startswith("insert"): # insert
                return "insert", string
            if string.startswith("end_insert"):
                return "end_insert", string    
            if string.startswith("provide"): # provide
                return "provide", string
            else:               # other type statements
                return "normal", string
        else:                   # html
            return "html", string.strip()
    def _find_end_insert(self, start_index): # find the `end_insert()` tag
        for index, string in enumerate(self.ir[start_index:]):
            string = string.getvalue()
            if string.startswith("++>") and string.endswith("<++")\
               and string[3:-3].strip().startswith("end_insert")\
               and string[3:-3].strip()[len("end_insert"):].strip()[0]=="(": # match  `(`
                return index+start_index
        raise SyntaxError("template SyntaxError: not found matched insert-->end_insert pair")

    def do_insert(self, string, start_index, end_index):
        """
        for `insert` statement, 
        set `self.base`, `self.insert_place`
        """
        assert(string.startswith("insert"))
        def insert(to, part):
            if not (HtmlPage.Instances.has_key(to)\
                    or os.path.exists(to)):         #  # not in HtmlPage.Instancesor this file not exists
                raise RuntimeError("not exists:" + to)
            if HtmlPage.Instances.has_key(to):
                self.base = HtmlPage.Instances[to]
            else:
                with open(to, "r") as f:
                    preparsed_f = preparse(f)
                    base = HtmlPage(origin=preparsed_f, name=to)
                    self.base = base
            self.insert_place.update({part: (start_index, end_index)})
        code_obj = compile(string, "template-compile", "exec")
        # exec `insert("xxx.html", "footer")`
        exec code_obj in locals()
    def _provided_name(self, string):
        """
        return the provided name:
        provide("xxx") -> xxx
        """
        ret = []
        def provide(part):
            ret.append(str(part))
        code_obj = compile(string, "template-compile", "exec")
        exec code_obj in {"provide": provide}
        if len(ret) == 1:
            return ret[0]
        raise LookupError("[_provide_name] failed")
    def do_provide(self, string, index):
        """
        for `provide` statement,
        set `self.provide_place`
        """
        assert(string.startswith("provide"))
        def provide(part):
            self.provide_place.append((part, index))
        code_obj = compile(string, "template-compile", "exec")
        # exec `provide("footer")`
        exec code_obj in locals()
    def do_normal(self, string):
        """
        for `other normal template statements`,
        execute them.
        """
        _append = Appender()
        def append(string):
            _append(string)
        code_obj = compile(string, "template-compile", "exec")
        env = self.env.copy()
        env.update({"append":append})
        exec code_obj in env # exec other normal template statements in environ `self.env`
        return _append.get_value() # 返回 这个 块 生成的html
    @property
    def env(self):
        if hasattr(self, "_env"):
            return self._env
        else:
            return None
    @env.setter
    def env(self, v):
        if hasattr(self, "_env"):
            self._env.update(v)
        else:
            self._env = dict(v)
        return self._env
        
# class FinalHtmlPage(HtmlPage):  # 貌似不用子类了。。。
#     def __init__(self, origin, **kwargs):
#         super(FinalHtmlPage, self).__init__(origin, **kwargs)

#     def render(self):
#         pass
    
# def parse(template_stack):
    # base = None
    # for stat in template_stack:
    #     if stat.startswith("++>") and 
    # pass

if __name__ == "__main__":
    import pdb, cStringIO
    test_html = """
    <aaa> aiheihei </aaa>
    ++> a+b <++
    <dfd><++ >++++>dfffefef \"sds\"<++
    <>fdfd<sdsd>
    """
    a=preparse(cStringIO.StringIO(test_html))
    test_html2 = """
    <aaa> aiheihei </aaa>
    ++> a+b <++
    <dfd><++ >++++>append(\"sds<++>++>\")<++
    <>fdfd<sdsd>>>>>++><++><>+><>+<>
    """
    env = {"a":1, "b":2}
    t2=HtmlPage(origin=preparse(cStringIO.StringIO(test_html2)), name="test_html2", **env)
    # t2.render()
    test3 = """
    <head>head<head>
    ++>append("head content here")<++
    <body>++>provide("body")<++<body>
    """
    test4 = """
    ++>insert("test3", "body")<++
    holy ++>append("sh"+"it")<++
    ++>end_insert()<++
    """
    t3 = HtmlPage(origin=preparse(cStringIO.StringIO(test3)), name="test3")
    t4 = HtmlPage(origin=preparse(cStringIO.StringIO(test4)), name="test4")
    t4.render()
    
