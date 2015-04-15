from wsgiref.util import setup_testing_defaults
from wsgiref.simple_server import make_server

import pdb
import cgi
from StringIO import StringIO
# A relatively simple WSGI application. It's going to print out the
# environment dictionary after being updated by setup_testing_defaults
def simple_app(environ, start_response):
    setup_testing_defaults(environ)

    status = '200 OK'
    headers = [('Content-type', 'text/plain')]

    start_response(status, headers)

    ret = ["%s: %s\n" % (key, value)
           for key, value in environ.iteritems()]
    safe_env = {"QUERY_STRING": ''}
    for k in ('REQUEST_METHOD', 'CONTENT_TYPE', 'CONTENT_LENGTH'):
        if k in environ: safe_env[k] = environ[k]
    # f = cgi.FieldStorage(fp=StringIO(environ['wsgi.input'].read(int(environ['CONTENT_LENGTH']))),
                         # environ=safe_env)
    pdb.set_trace()
    f = cgi.FieldStorage(fp=StringIO(environ['wsgi.input'].read(int(environ['CONTENT_LENGTH']))), environ=safe_env)

    # ret += [environ['wsgi.input'].read(1000)+'\n']
    return ret

httpd = make_server('', 8080, simple_app)
print "Serving on port 8080..."
httpd.serve_forever()
