from .. import cap
import pdb

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
    pdb.set_trace()
    f = cap.request.POST.get("ee", None)
    return cap.Response(
        body="<h1>INdEx</h1><p>args:%s</p><p>GET:%s</p><p>POST:%s</p>"%(str(args), cap.request.GET, cap.request.POST)
    )

@cap.root.route(r"/")
def root(*args):
    return cap.Response(
        body="<h1>root page</h1>"
    )
cap.run(8080, "127.0.0.1")
