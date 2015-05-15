#coding:utf-8#
import sys
sys.path.append("../")
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

# models
from cap.db import db
db.db_bind(host="localhost", user="learnguy", passwd="uefgsigw", db="learn")
class TestModel_1(db.Model):
    f1 = db.CharField(max_length=123)
    f2 = db.DateTimeField(auto_update=True, auto_now=True)

try:
    db.create_table(TestModel_1)
except Exception:
    pass


@cap.root.route(r"db/(\w+)")
def test_db(*args):
    model_ins = TestModel_1(f1=args[0])
    model_ins.save()
    
    return cap.Response(body="save %s"%args[0])

@cap.root.route(r"db2/(\w+)")
def test_db_2(*args):
    res = TestModel_1.filter(f1=args[0])
    if not res:
        return cap.Response(body="empty")
    return cap.Response(body=str(res[0].f2))


cap.run(8081, "107.170.196.218")
