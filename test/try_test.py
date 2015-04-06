from .. import cap

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
@mainrouter.route(r"/index/(\w*)")
def index(*args):
    return cap.Response(body="<h1>INdEx</h1><p>args:%s</p>"%str(args))

@mainrouter.route(r"/download/")
def download():
    import os
    f = open("/Users/rcmerci/Desktop/屏幕快照 2015-03-03 下午2.04.14.png","rb")
    size = os.stat("/Users/rcmerci/Desktop/屏幕快照 2015-03-03 下午2.04.14.png").st_size
    return cap.MediaRespnse(f.read(size))
cap.run(8080, "127.0.0.1")
