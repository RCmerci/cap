import template

test2html = template.Template("./test2.html")

ret = test2html.render(**{"env1":"environ var 1", "env2":"environ var 2"})

print ret.getvalue()
