from .. import cap

router = cap.Router("prefix")
app = cap.Cap(router)
cap.app_register(app)
@router.route("testurl")
def test_f(*args):
    print args
    return cap.Response(body="body")

mainrouter = cap.Router("main")
mainapp = cap.Cap(mainrouter)
cap.app_register(mainapp)
@mainrouter.route("/index")
def index(*args):
    return cap.Response(body="<h1>INdEx</h1><p>args:%s</p>"%str(args))
cap.run(8080, "127.0.0.1")
