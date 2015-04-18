#coding:utf-8#
import sys
sys.path.append("../..")
from cap import cap
import pdb
from cap.template.template import Template
router = cap.Router(r"prefix")
app = cap.Cap(router)
cap.app_register(app)
@router.route(r"testurl")
def test_f(*args):
    print args
    return cap.Response(body="body")

mainrouter = cap.Router(r"main")
mainapp = cap.Cap(mainrouter)
cap.app_register(mainapp)
@mainrouter.route(r"/index/")
def index(*args):
    return cap.Response(
        body="<h1>INdEx</h1><p>args:%s</p><p>GET:%s</p><p>POST:%s</p>"%(str(args), cap.request.GET, cap.request.POST)
    )

@mainrouter.route(r"/download/")
def download():
    import os
    f = open("/Users/rcmerci/Desktop/屏幕快照 2015-03-03 下午2.04.14.png","rb")
    size = os.stat("/Users/rcmerci/Desktop/屏幕快照 2015-03-03 下午2.04.14.png").st_size
    return cap.MediaRespnse(f.name)

@mainrouter.route(r"/", "post")
def aiheihei(*args):
    f = cap.request.POST.get("ee", None)
    return cap.Response(
        body="<h1>INdEx</h1><p>args:%s</p><p>GET:%s</p><p>POST:%s</p>"%(str(args), cap.request.GET, cap.request.POST)
    )

@cap.root.route(r"/")
def root(*args):
    return cap.Response(
        body="<h1>root page</h1>"
    )
@cap.root.route(r"/test/template")
def test_template(*args):
    html = Template("./test2.html")
    context = {"env1":"val1", "env2":"val2"}
    return cap.Response(
        body=html.render(**context)
    )
#cap.run(8080, "127.0.0.1")
 # def application(a, b):
 #     return cap.application(a, b)
