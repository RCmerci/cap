#coding:utf-8#
import re, os
from cStringIO import StringIO

class Template(object):
    pass



def insert(html, to, part_name):
    pass

def end_insert():
    pass

def provide(part_name):
    pass

def append(string):             # unused
    pass

class Appender(object):
    def __init__(self):
        self._content = []
    def __call__(self, string):
        self._content.append(str(string))
    def __exit__(self):
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
    pdb.set_trace()
    return template_stack




class HtmlPage(object):
    Instances = {}
    def __init__(self, name, origin, **kwargs):
        self.base = None
        self.sub = None         # 好像没有用
        self.origin = origin
        self.ir = origin
        self.insert_place = {}
        self.provide_place = []
        self.name = name
        HtmlPage.Instances.update({self.name: self}) # add self to class level val
        ######### init followed
        self.scan()
        self.env = kwargs
    def scan(self):
        for index, stat in enumerate(self.ir):
            tp, string = self.identify(stat)
            if tp == "insert":
                end_index = self._find_end_insert(index + 1)
                self.do_insert(string, index, end_index)
            elif tp == "provide":
                self.do_provide(string)
            elif tp == "normal":

                
            else:               # html 
                pass
        pass
    def identify(self, string):
        if string.startswith("++>") and string.endswith("<++"):
            string = string[3:-3].strip()
            if string.startswith("insert"): # insert
                return "insert", string
            if string.startswith("provide"): # provide
                return "provide", string
            else:               # other type statements
                return "normal", string
        else:                   # html
            return "html", string.strip()
    def _find_end_insert(self, start_index): # find the `end_insert()` tag
        for index, string in enumerate(self.ir[start_index:]):
            if string.startswith("++>") and string.endswith("<++")\ # match `++>`and`<++`
               and string[3:-3].strip().startswith("end_insert")\ # match `end_insert`
               and string[3:-3].strip()[len("end_insert"):].strip()[0]=="(": # match  `(`
                return index
        raise SyntaxError("template SyntaxError: not found matched insert-->end_insert pair")

    def do_insert(self, string, start_index, end_index):
        """
        for `insert` statement, 
        set `self.base`, `self.insert_place`
        """
        assert(string.startswith("insert"))
        def insert(to, part):
            if not (HtmlPage.Instances.has_key(to)\ # not in HtmlPage.Instances
                    or os.path.exists(to)):         #  this file not exists
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
        exec code_obj           # exec `insert("xxx.html", "footer")`
    def do_provide(self, string):
        """
        for `provide` statement,
        set `self.provide_place`
        """
        assert(string.startswith("provide"))
        def provide(part):
            self.provide_place.append(part)
        code_obj = compile(string, "template-compile", "exec")
        exec code_obj           # exec `provide("footer")`
    def do_normal(self, string):
        """
        for `other normal template statements`,
        execute them.
        """
        code_obj = compile(string, "template-compile", "exec")
        exec code_obj in self.env
    @property
    def env(self):
        if self._env:
            return self._env
        else:
            return None
    @env.setter
    def env(self, v):
        self._env.update(v)
        return self._env
        
class FinalHtmlPage(HtmlPage):
    def __init__(self, origin, **kwargs):
        super(FinalHtmlPage, self).__init__(origin, **kwargs)

    def render(self):
        pass
    
def parse(template_stack):
    base = None
    for stat in template_stack:
        if stat.startswith("++>") and 
    pass

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
    <dfd><++ >++++>dfffefef \"sds<++>++>\"<++
    <>fdfd<sdsd>>>>>++><++><>+><>+<>
    """
    preparse(cStringIO.StringIO(test_html2))
