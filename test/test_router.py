import sys
sys.path.append("..")
from cap.cap import Router, Cap
import pdb
from cap.utils import FormatReUrl
def donothing(): pass

#                     r1
#                     / \
#                    /   \
#                   r2   r3 
#                         | 
#                         | 
#                         r4
#                     
                      
r1 = Router("r1")     
c1 = Cap(r1)          
r2 = Router("r2")     
c2 = Cap(r2)          
r3 = Router("r3")     
c3 = Cap(r3)          
r4 = Router("r4")     
c4 = Cap(r4)          

c1.subapp(c2)
c1.subapp(c3)
c3.subapp(c4)

r2.add("r2_func", donothing)
r4.add("", donothing)
pdb.set_trace()
url1 = FormatReUrl("r2/r2_func")
assert(r1.search(str(url1), "get")[0] == c2)
assert(r2.search(url1.consume_prefix().url, "get")[0] == donothing)
url2 = FormatReUrl("r3/r4/")
assert(r1.search(url2.url, "get")[0] == c3)
assert(r3.search(url2.consume_prefix().url, "get")[0] == c4)
assert(r4.search(url2.consume_prefix().consume_prefix().url, "get")[0] == donothing)
