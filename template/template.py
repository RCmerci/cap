#coding:utf-8#
import re
from cStringIO import StringIO

class Template(object):
    pass



def insert(html, to, part_name):
    pass

def end_insert():
    pass

def provide(part_name):
    pass

def append(string):
    pass


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
