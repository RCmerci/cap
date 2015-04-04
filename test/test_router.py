from cap import Router


def lookup(ins):
    return (
        ins.prefix,
        ins.fallback,
        ins.get,
        ins.post,
        ins.head,
        ins.other,
        ins.router_instances
    )


def new_ins(prefix):
    return Router(prefix)



def passfunc():pass

def case1():
    ins = Router("case1")



    # !!!!!!!!!!!! TODO 测试以后再写 = = 。。。。。


