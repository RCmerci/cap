class BaseField(object):
    specific_arg_with_default = (
        ("verbose", ""),
        ("null", True),
        ("blank", True),
        # ("default", "")  //`default` arg's default value for diff field vary a lot
        #                  // so it should assign at its sub class.
    )
    def __init__(self, **kwargs):
        mro = [i for i in self.__class__.mro() if i is not object]
        summary_sawd = {}       # sawd: specific_arg_with_default
        for cls in mro:
            summary_sawd.update(dict(cls.specific_arg_with_default))
        summary_sa = summary_sawd.keys() # sa: specific_arg, not include default values
        for k, v in kwargs.items():
            if k in summary_sa:
                setattr(self, k, v)
        for k in summary_sa:
            if not hasattr(self, k):
                setattr(self, k, summary_sawd[k])
                
    def __str__(self):
        raise NotImplementedError("sub class should implement it")
    __repr__ = __str__

    
class CharField(BaseField):
    specific_arg_with_default = (
        ("max_length", 255),
        ("default", ""),
    )
    sql_data_type = "VERCHAR({max_length})"

    def __init__(self, **kwargs):
        super(CharField, self).__init__(**kwargs) # 平常，父类的init貌似总在最后调用，而这里父类的init是用
        pass                                      # 来assgin一些变量，后面要用到。
        self.sql_data_type = self.sql_data_type.format(max_length=self.max_length)
        
    def __str__(self):
        return "<CharField id:{0} VARCHAR({1})>".format(id(self), self.sql_data_type%self.max_length)


class IntField(BaseField):
    pass
class FloatField(BaseField):
    pass
class TextField(BaseField):
    pass
class DateTimeField(BaseField):
    pass


# def unique_list(l):             # unused
#     """
#     example:
#     l -> ((1,2), (2,3), (1,3))
#     result -> ((2,3), (1,3))
#     -------------------------
#     remove the pairs which has same key , (first val as key , 2nd as value).
#     reserve the last pair.
#     """
#     res = {}
#     for k, v in l:
#         res[k] = v
#     return tuple(res.iteritems())
    
class DBError(Exception):
    pass

class MetaModel(type):
    def __init__(cls, name, bases, dic):
        sql_create = """
        CREATE TABLE {tbl_name} ({fields})
        """
        # 合成 sql table 的 create 语句
        # `fields`
        fields = {}
        for fname, v in dic:
            if not isinstance(v, BaseField):
                pass
            fields.update({fname: v.sql_data_type})
        sql_fields = ", ".join(["%s %s"%(k, v) for k, v in fields.items()])
        _sql_create = sql_create.format(fields=sql_fields)
        _fields = fields.keys()
        new_dic = dic.update({                             # new_dic 内容：
            "_sql_create": _sql_create,                    # 各种field的instance（CharField），
            "_fields": fields                              # _sql_create: model 的 sql 创建语句
        })                                                 # _fields : 各个fields的名字
                                                    
        # set up `Query`
        qname = None
        query = None
        for fname, v in dic:
            if isinstance(v, Query):
                query = v
                qname = fname
                break
        query.meta_fill(**new_dic)

        super(MetaModel, cls).__init__(name, bases, new_dic)


class Model(object):
    __metaclass__ = MetaModel
    query = Query()

class Query(object):
    """
    a bundle of functions for db quering.

    arg_keywords = (
        "contain",              # string
        "startswith",
        "endswith",
        
        "gt",                   # date and number
        "ge",
        "lt",
        "le",
        "between", ///这个不需要。。而且有4种情况，所以用gt,ge,lt,le组合就好了。
        "eq",
        "ne",
    )
    """
    kw2sql = {
        "contain": "{0} LIKE '%{1}%'",
        "startswith": "{0} LIKE '{1}%'",
        "endswith": "{0} LIKE '%{1}'",
        "gt": "{0} > {1}",
        "ge": "{0} >= {1}",
        "lt": "{0} < {1}",
        "le": "{0} <= {1}",
        "eq": "{0} = {1}",
        "ne": "{0} <> {1}",
    }
    def __init__(self, **kwargs):
        self.fields = []
        
    def meta_fill(self, **kwargs):
        # append model's field name into `self.fields`
        kw = kwargs.copy()
        kw.pop("_sql_create")
        for k, v in kw.items():
            if isinstance(v, BaseField):
                self.fields.append(k)
                
    @staticmethod
    def _arg2sql(**kwargs):
        # combine kwargs into sql according to `kw2sql`
        res = []
        for k, v in kwargs.items():
            ks = k.rsplit("__", 1) # example:  aa__contain -> ks[0]==aa, ks[1]==contain
            if len(ks) == 2 and ks[1] in kw2sql.keys():
                res.append(kw2sql[ks[1]].format(ks[0], v))
            res.append("%s = %s"%(k, v))            # default case: a=b
        return " and ".join(res)
    
    def get(**kwargs):
        _sql = self.__class__._arg2sql(**kwargs)
        
        pass
    



class LazyQ(object):
    """
    a lazy object for sql result,
    calculate when it is really needed.
    """
    from ..utils import calculate_once
    def __init__(self, executor):
        self.executor = executor

    @calculate_once
    def _execute(self):
        return self.executor()
    
    def __iter__(self):
        res = self._execute()
        return iter(res)
    
    def __repr__(self):
        res = self._execute()
        return res


class DBCompiler(object):
    class SqlObj(object):
        def __init__(self, sql_tp): # sql_tp: one of [select, insert, delete, update]
            self.sql = [sql_tp.upper()]
        def _append(self, sql):
            self.sql.append(sql)
        def __getattribute__(self, name):
            func = getattr(DBCompiler, name)
            if callable(func):
                return self._wrapfunc(func)
            raise RuntimeError("no such function in DBCompiler: %s"%name)
        def _wrapfunc(self, func):
            def aux(sql):
                self._append(func(sql))
                return self
            return aux
        def render(self):
            return " ".join(self.sql)
        
    @staticmethod
    def select():
        return SqlObj("select")

    @staticmethod
    def insert():
        return SqlObj("insert")

    @staticmethod
    def delete():
        return SqlObj("delete")

    @staticmethod
    def update():
        return SqlObj("update")

    
