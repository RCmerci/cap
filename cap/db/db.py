class BaseField(object):
    specific_arg_with_default = (
        ("verbose", ""),
        ("null", True),
        ("blank", True),
        ("pk", False),
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
                
    def __repr__(self):
        raise NotImplementedError("sub class should implement it")

    
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
        
    def __repr__(self):
        return "<CharField at:{0}, {1}>".format(hex(id(self)), self.sql_data_type)


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
        if len(cls.mro()) > 2: # means it is not `Model`(the base model).
            # 合成 sql table 的 create 语句
            # `fields`
            fields = {}
            _pk_flag = False
            cls._pk = None
            for fname, v in dic:
                if not isinstance(v, BaseField):
                    continue
                if v.pk and not _pk_flag:
                    cls._pk = fname
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
            # query.meta_fill(**new_dic)
            query.meta_fill(cls)
        else:
            new_dic = dic
        super(MetaModel, cls).__init__(name, bases, new_dic)


# class Model(object):
#     __metaclass__ = MetaModel
#     query = Query()
#     def _re_structure(self, **kwargs):
#         for k, v in kwargs:
#             setattr(self, k, v)

#     def __repr__(self):
#         if not self.__class__._pk:
#             _pk = 'no pk assigned'
#         else:
#             _pk = getattr(self, str(self.__class__._pk))
#         return "<{name}:{pk}>".format(
#             name=self.__class__.__name__,
#             pk=getattr(self, str(self.__class__._pk))
#         )

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
        
    def meta_fill(self, model):
        self.model = model
        
    @classmethod
    def _arg2sql(cls, **kwargs):
        # combine kwargs into sql according to `kw2sql`
        res = []
        for k, v in kwargs.items():
            ks = k.rsplit("__", 1) # example:  aa__contain -> ks[0]==aa, ks[1]==contain
            if len(ks) == 2 and ks[1] in cls.kw2sql.keys():
                res.append(kw2sql[ks[1]].format(ks[0], v))
            res.append("%s = %s"%(k, v))            # default case: a=b
        return " AND ".join(res)
    
    def get(**kwargs):
        cond = self.__class__._arg2sql(**kwargs)
        sql = DBCompiler.Combiner.get(cond)
        raw_res = local_dic.DBexecutor(sql)
        if len(raw_res) > 1:
            raise DBError("got more than 1 instance")
        return re_structure(self.model, raw_res)
    
    def all(self):
        return LazyQ(local_dic.DBexecutor, method="all", model=self.model)

    def filter(self, **kwargs):
        cond = self.__class__._arg2sql(**kwargs)
        return LazyQ(local_dic.DBexecutor, method="filter", cond=cond, model=self.model)


class Model(object):
    __metaclass__ = MetaModel
    query = Query()

    def __repr__(self):
        if not self.__class__._pk:
            _pk = 'no pk assigned'
        else:
            _pk = getattr(self, str(self.__class__._pk))
        return "<{name}:{pk}>".format(
            name=self.__class__.__name__,
            pk=getattr(self, str(self.__class__._pk))
        )
    # class Meta:
    #     abstract = True

class LazyQ(object):
    """
    a lazy object for sql result,
    calculate when it is really needed.
    """
    DEBUG = True
    if DEBUG == True:
        import sys
        sys.path.append("..")
        from utils import calculate_once
    else:
        from ..utils import calculate_once
    
    def __init__(self, executor, model, method, init=True, cond=""):
        self.executor = executor
        if init:
            self.init_method = method
            self.init_cond = cond
            self.follow_method = []
            self.model = model
        else:
            self.follow_method.append(method)
        
    @calculate_once
    def _execute(self):
        combiner = getattr(DBCompiler.Combiner, self.init_method)
        if self.init_cond:
            sql = combiner(self.model, self.init_cond)
        else:
            sql = combiner(self.model)
        raw_res = self.executor(sql)
        return re_structure(self.model, raw_res)

    # magic method followed ...
    def __iter__(self):
        res = self._execute()
        return iter(res)
    
    def __repr__(self):
        res = self._execute()
        return str(res)

    def __nonzero__(self):
        res = self._execute()
        return bool(res)

    def __contains__(self, item):
        res = self._execute()
        return item in res

    def __getitem__(self, k):
        if not isinstance(k, int):
            raise RuntimeError("LazyQ is only list-like")
        res = self._execute()
        return res[k]

    # method on LazyQ
    def get(self):
        pass
    def filter(self):
        pass
    def all(self):
        pass


class DBCompiler(object):
    class SqlObj(object):
        def __init__(self, sql_tp): # sql_tp: one of [select, insert, delete, update]
            self.sql = [sql_tp.upper()]
        def append(self, sql):
            self.sql.append(sql)
        def __getattr__(self, name):
            func = getattr(DBCompiler, name)
            if callable(func):
                return self._wrapfunc(func)
            raise RuntimeError("no such function in DBCompiler: %s"%name)
        def _wrapfunc(self, func):
            def aux(*args, **kwargs):
                self.append(func(*args, **kwargs))
                return self
            return aux
        def render(self):
            return " ".join(self.sql)
        
    @classmethod
    def Select(cls):
        return cls.SqlObj("select")

    @classmethod
    def Insert(cls):
        return cls.SqlObj("insert")

    @classmethod
    def Delete(cls):
        return cls.SqlObj("delete")

    @classmethod
    def Update(cls):
        return cls.SqlObj("update")

    @classmethod
    def All(cls, model):
        return ", ".join(cls.all_fields(model))
    @staticmethod
    def From(model):
        return "FROM " + model.__name__

    @staticmethod
    def Where(condition):
        return "WHERE " + condition

    @staticmethod
    def Group_by(model, col_name, asc_or_desc="ASC"):
        return "GROUP BY {0}.{1} {2}".format(
            model.__name__,
            col_name,
            asc_or_desc.upper()
        )

    @staticmethod
    def Order_by(model, col_name, asc_or_desc="ASC"):
        return "ORDER BY {0}.{1} {2}".format(
            model.__name__,
            col_name,
            asc_or_desc.upper()
        )

    @staticmethod
    def Limit(num, startfrom=0):
        return "LIMIT {startfrom}, {number}".format(
            startfrom=startfrom,
            number=num
        )

    @staticmethod
    def Into(model, col_name_l=None):
        if not col_name_l:
            col_name_l = self.all_fields()
        col_names = ", ".join(col_name_l)
        return "INTO {tbl} ({cols})".format(
            tbl=model.__name__,
            cols=col_names
        )

    @staticmethod
    def Values(values_l):       # insert
        _valuess = ", ".join([str(tuple(values)) for values in values_l])
        return "VALUES {0}".format(
            _valuess
        )

    @staticmethod
    def Set(model, field_val_dic): # update
        res = []
        for k, v in field_val_dic.items():
            res.append(model.__name__ + k + "=" + str(v))
        res = ", ".join(res)
        return "SET {0}".format(res)



    # ----------------------------------------------------------------
    @staticmethod
    def all_fields(model):
        return [model.__name__ + "." + fn for fn in model._fields]
    
    class Combiner(object):
        @classmethod
        def all(cls, model):
            return cls.__class__.Select().All(model).From(model).render()

        @classmethod
        def filter(cls, model, cond):
            return cls.__class__.Select().All(model).From(model).Where(cond).render()

        @classmethod
        def get(cls, model, cond):
            return cls.__class__.\
                Select().All(model).\
                From(model).Where(cond).render() # 和 `filter` 一样， 但get的话，之后要判断是不是只有一个。
                
        # 现在只实现了 all，get和filter。。其他的之后再加上



class Executor(object):
    import MySQLdb
    def bind(**kwargs):
        self.db = MySQLdb.connect(**kwargs)
        self.cur = self.db.cursor()

    def __call__(self, sql):
        self.cur.execute(sql)
        self.db.commit()
        return self.cur.fetchall()


def re_structure(modelcls, raw_res):
    if not raw_res:
        return []
    if len(raw_res[0]) <> len(modelcls._fields):
        raise DBError(u"database返回的值字段个数与model不相等，这个不应该发生－ －")
    res = []
    for ins in raw_res:
        model_ins = modelcls()
        for fname in modelcls._fields:
            setattr(model_ins, fname, )
        res.append(model_ins)
    return res
        
from ..cap import local_dic
def db_bind(**kwargs):
    local_dic.DBexecutor = Executor()
    local_dic.DBexecutor.bind(**kwargs)
