# -*- coding: utf-8 -*-
import pdb
import warnings
if __name__ == '__main__':
    DEBUG = True

    
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

    def validate(self, v):
        raise NotImplementedError("sub class should implement it")
    
class CharField(BaseField):
    specific_arg_with_default = (
        ("max_length", 255),
        ("default", ""),
    )
    sql_data_type = "VERCHAR({max_length})"
    str_like = True             # 表示 CharField 的值的类字符串的。(sql 里要加引号)
    
    def __init__(self, **kwargs):
        super(CharField, self).__init__(**kwargs) # 平常，父类的init貌似总在最后调用，而这里父类的init是用
        pass                                      # 来assgin一些变量，后面要用到。
        self.sql_data_type = self.sql_data_type.format(max_length=self.max_length)
        
    def __repr__(self):
        return "<CharField at:{0}, {1}>".format(hex(id(self)), self.sql_data_type)

    def validate(self, v):
        if isinstance(v, basestring):
            return True
        return False

class IntField(BaseField):
    pass
class FloatField(BaseField):
    pass
class TextField(BaseField):
    pass
class DateTimeField(BaseField):
    pass


class DBError(Exception):
    pass

class MetaModel(type):
    def __new__(meta, name, bases, dic):
        sql_create = """
        CREATE TABLE {tbl_name} ({fields})
        """
        if not bases[0] is object: # means it is not `Model`(the base model).
            # 合成 sql table 的 create 语句
            # `fields`
            fields = {}
            _pk_flag = False
            _pk = None
            for fname, v in dic.items():
                if not isinstance(v, BaseField):
                    continue
                if v.pk and not _pk_flag:
                    _pk = fname
                    _pk_flag = True
                dic.update({fname: field_descr(v, fname)}) # descr for fields
                    
                fields.update({fname: v.sql_data_type})
                
            sql_fields = ", ".join(["%s %s"%(k, v) for k, v in fields.items()])
            _sql_create = sql_create.strip().format(
                tbl_name=name,
                fields=sql_fields
            )
            _fields = fields.keys()
            dic.update({                                        # dic 内容：
                "_sql_create": _sql_create,                    # 各种field的instance（CharField），
                "_fields": _fields,                              # _sql_create: model 的 sql 创建语句
                "_pk": _pk,
            })                                                 # _fields : 各个fields的名字
        else:
            pass
        return super(MetaModel, meta).__new__(meta, name, bases, dic)

    @staticmethod
    def find_query_ins(cls):
        for i in dir(cls):
            if isinstance(getattr(cls, i), Query):
                return (i, getattr(cls, i))
            
    def __init__(cls, name, bases, dic):
        if not bases[0] is object:
            qname, query = MetaModel.find_query_ins(cls)
            query.meta_fill(cls)
        super(MetaModel, cls).__init__(name, bases, dic)


class NotExistError(Exception):
    pass

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
        "gt": "{0} > {sl}{1}{sl}",
        "ge": "{0} >= {sl}{1}{sl}",
        "lt": "{0} < {sl}{1}{sl}",
        "le": "{0} <= {sl}{1}{sl}",
        "eq": "{0} = {sl}{1}{sl}",
        "ne": "{0} <> {sl}{1}{sl}",
    }
    def __init__(self, **kwargs):
        #self.fields = []
        pass
        
    def meta_fill(self, model):
        self.model = model
    
    def _arg2sql(self, **kwargs):
        return arg2cond(self.model)(**kwargs)
        # combine kwargs into sql according to `kw2sql`
        # res = []
        # for k, v in kwargs.items():
        #     ks = k.rsplit("__", 1) # example:  aa__contain -> ks[0]==aa, ks[1]==contain
        #     if ks[0] not in self.model._fields:
        #         raise DBError("illegal db query")
        #     sl = "\"" if getattr(self.model, ks[0]).str_like else ""
        #     if len(ks) == 2 and ks[1] in self.kw2sql.keys():
        #         res.append(self.kw2sql[ks[1]].format(ks[0], v, sl=sl))
        #     res.append(self.kw2sql["eq"].format(ks[0], v, sl=sl))            # default case: a=b
        # return " AND ".join(res)
    
    def get(self, **kwargs):
        cond = self._arg2sql(**kwargs)
        sql = DBCompiler.Combiner.get(self.model, cond)
        raw_res = local_dic.DBexecutor(sql)
        if len(raw_res) > 1:
            raise DBError("got more than 1 instance")
        if len(raw_res) == 0:
            raise NotExistError()
        return re_structure(self.model, raw_res)[0]
    
    def all(self):
        return LazyQ(local_dic.DBexecutor, method="all", model=self.model)

    def filter(self, **kwargs):
        cond = self._arg2sql(**kwargs)
        return LazyQ(local_dic.DBexecutor, method="filter", cond=cond, model=self.model)

    def save(self, model_ins):
        if model_ins.is_update:
            cond = self._arg2sql(**model_ins.old_kv_dic())
            new_val_dic = model_ins.new_kv_dic()
            sql = DBCompiler.Combiner.update(self.model, cond, new_val_dic)
            local_dic.DBexecutor(sql)
        else:
            new_val_dic = model_ins.new_kv_dic()
            sql = DBCompiler.Combiner.insert(self.model, new_val_dic)
            local_dic.DBexecutor(sql)
_kw2sql = {
    "contain": "{0} LIKE '%{1}%'",
    "startswith": "{0} LIKE '{1}%'",
    "endswith": "{0} LIKE '%{1}'",
    "gt": "{0} > {sl}{1}{sl}",
    "ge": "{0} >= {sl}{1}{sl}",
    "lt": "{0} < {sl}{1}{sl}",
    "le": "{0} <= {sl}{1}{sl}",
    "eq": "{0} = {sl}{1}{sl}",
    "ne": "{0} <> {sl}{1}{sl}",
}

def arg2cond(model):         # convert args to sql WHERE's content(condtion)
    def aux(**kwargs):
        res = []
        for k, v in kwargs.items():
            ks = k.rsplit("__", 1)
            if ks[0] not in model._fields:
                warnings.warn("KeyWarning: {0}, not exist.".format(ks[0]))
                continue
            sl = "\"" if getattr(model, ks[0]).str_like else ""
            if len(ks) == 2 and ks[1] in _kw2sql.keys():
                res.append(_kw2sql[ks[1]].format(ks[0], v, sl=sl))
            res.append(_kw2sql["eq"].format(ks[0], v, sl=sl))
        return " AND ".join(res)
    return aux
            
class field_descr(object):
    def __init__(self, field, name):
        self._field = field
        self._name = name
        
    def __get__(self, obj, owner):
        if obj == None:
            return self._field
        if hasattr(obj, "_new_"+self._name):
            res = getattr(obj, "_new_"+self._name)
        else:
            res = getattr(obj, "_old_"+self._name)
        return res
    
    def __set__(self, obj, val):
        if hasattr(obj, "_old_"+self._name):
            setattr(obj, "_new_"+self._name, val)
        else:
            setattr(obj, "_old_"+self._name, val)

    @staticmethod
    def fresh(descr, obj):
        if not hasattr(obj, "_old_"+descr._name):
            raise RuntimeError("can't fresh, no old val `%s`."%descr._name)
        if not hasattr(obj, "_new_"+descr._name):
            return
        setattr(obj, "_old_"+descr._name, getattr(obj, "_new_"+descr._name))

    @staticmethod
    def old_val(descr, obj):
        return getattr(obj, "_old_"+descr._name)

    @staticmethod
    def new_val(descr, obj):
        if hasattr(obj, "_new_"+descr._name):
            return getattr(obj, "_new_"+descr._name)
        else:
            return getattr(obj, "_old_"+descr._name)

    def __repr__(self):
        return "<%s>"%self._name
    
class Model(object):
    __metaclass__ = MetaModel
    query = Query()

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    
    def __repr__(self):
        if not self.__class__._pk:
            _pk = 'no pk assigned'
        else:
            _pk = getattr(self, str(self.__class__._pk))
        return "<{name}:{pk}>".format(
            name=self.__class__.__name__,
            pk=_pk
        )

    @property
    def is_update(self):
        if not hasattr(self, "_isupdate"):
            return False
        return self._isupdate
    @is_update.setter
    def is_update(self, v):
        self._isupdate = bool(v)

    def get(self, **kwargs):
        return self.query.get(**kwargs)

    def all(self):
        return self.query.all()

    def filter(self, **kwargs):
        return self.query.filter(**kwargs)
    
    def save(self):
        if self.old_kv_dic() == self.new_kv_dic():
            return
        self.query.save(self)
        for k in self._fields:
            field_descr.fresh(self.__class__.__dict__[k], self)
        self.is_update = True

    # --------------------------------------------------------------
    def old_kv_dic(self):
        """
        返回 instance 的键值（_fields里的） 字典, (old_val)
        """
        res_tuple = []
        for k in self._fields:
            res_tuple.append((k, field_descr.old_val(self.__class__.__dict__[k], self)))
        return dict(res_tuple)

    def new_kv_dic(self):
        """
        返回 instance 的键值（_fields里的） 字典, (new_val)
        """
        res_tuple = []
        for k in self._fields:
            res_tuple.append((k, field_descr.new_val(self.__class__.__dict__[k], self)))
        return dict(res_tuple)

class LazyQ(object):
    """
    a lazy object for sql result,
    calculate when it is really needed.
    """
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
            self.follow_kwargs_cond = [] # 
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
        res = self._exec_all()
        return iter(res)

    def __len__(self):
        res = self._exec_all()
        return len(res)
    
    def __repr__(self):
        res = self._exec_all()
        return str(res)

    def __nonzero__(self):
        res = self._exec_all()
        return bool(res)

    def __contains__(self, item):
        res = self._exec_all()
        return item in res

    def __getitem__(self, k):
        if not isinstance(k, int):
            raise RuntimeError("LazyQ is only list-like")
        res = self._exec_all()
        return res[k]

    # method on LazyQ--------------------------------
    def get(self, **kwargs):
        res = self._exec_all()
        if len(res) == 0:
            raise NotExistError()
        if len(res) > 1:
            raise DBError("got more than 1 instance")
        return res[0]

    def filter(self, **kwargs):
        self.follow_method.append("filter")
        self.follow_kwargs_cond.append(kwargs)
        return self
    
    def all(self):              # just do nothing
        return self

    # --------------------utils----------------------------
    def _filter(self, mid_res, **kwargs):
        fields_cmp = []
        for k, v in kwargs:
            ks = k.rsplit("__", 1)
            cmp_kw = ks[1] if len(ks)==2 else None
            fields_cmp.append((ks[0], cmp_kw, v))
        def aux(model_ins):
            fields = [k for k, cmp_kw, v in fields_cmp]
            for f in [f for f in model_ins._fields if f in fields]:
                for k, cmp_kw, cmp_cnt in fields_cmp:
                    if k == f and\
                       self._cmp(cmp_kw, cmp_cnt, getattr(model_ins, f)):
                        break
                    elif k == f:
                        return False
            return True
        return filter(aux, mid_res)

                        
    def _cmp(self, kw, cmp_cnt, cmped_cnt):
        import re
        if isinstance(cmp_cnt, basestring):
            if kw == "contain" and re.search(cmp_cnt, cmped_cnt):
                return True
            if kw == "startswith" and cmped_cnt.startswith(cmp_cnt):
                return True
            if kw == "endswith" and cmped_cnt.endswith(cmp_cnt):
                return True
            return False
        else:
            if kw == "gt" and cmped_cnt > cmp_cnt:
                return True
            if kw == "ge" and cmped_cnt >= cmp_cnt:
                return True
            if kw == "lt" and cmped_cnt < cmp_cnt:
                return True
            if kw == "le" and cmped_cnt <= cmp_cnt:
                return True
            if kw == "eq" and cmped_cnt == cmp_cnt:
                return True
            if kw == "ne" and cmped_cnt <> cmp_cnt:
                return True
            return False
        
    def _exec_all(self):
        # TODO: 这个方法：得到db那里的结果，然后，把follow_method执行一遍，
        # 但是每次调用他，follow_method都会执行一遍，应该cache起来
        dbres = self._execute()
        mid_res = dbres
        for method, kwargs in zip(self.follow_method, self.follow_kwargs_cond):
            mid_res = getattr(self, "_"+method)(mid_res, **kwargs)
        return mid_res


    
class DBCompiler(object):
    class SqlObj(object):
        def __init__(self, sql_tp): # sql_tp: one of [select, insert, delete, update]
            self.sql = [sql_tp.upper()]
        def append(self, sql):
            self.sql.append(sql)
            return self
        def __getattr__(self, name):
            func = getattr(DBCompiler, name)
            if callable(func):
                return self._wrapfunc(func)
            raise RuntimeError("no such function in DBCompiler: %s"%name)
        def _wrapfunc(self, func):
            def aux(*args, **kwargs):
                return self.append(func(*args, **kwargs))
            return aux
        def render(self):
            return " ".join(self.sql)
        
    @classmethod
    def Select(cls):
        return cls.SqlObj("select")

    @classmethod
    def Insert(cls, model):
        return cls.SqlObj("insert").append(model.__name__)

    @classmethod
    def Delete(cls):
        return cls.SqlObj("delete")

    @classmethod
    def Update(cls, model):
        return cls.SqlObj("update").append(model.__name__)

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
            sl = "\"" if model.str_like else ""
            res.append("{name} = {sl}{val}{sl}".format(
                name=model.__name__+"."+k,
                sl=sl,
                val=str(v)
            ))
        res = ", ".join(res)
        return "SET {0}".format(res)



    # ----------------------------------------------------------------
    @staticmethod
    def all_fields(model):
        return [model.__name__ + "." + fn for fn in model._fields]
    
    class Combiner(object):
        @staticmethod
        def all(model):
            return DBCompiler.Select().All(model).From(model).render()

        @staticmethod
        def filter(model, cond):
            return DBCompiler.Select().All(model).From(model).Where(cond).render()

        @staticmethod
        def get(model, cond):
            return DBCompiler.\
                Select().All(model).\
                From(model).Where(cond).render() # 和 `filter` 一样， 但get的话，之后要判断是不是只有一个。
                
        @staticmethod
        def update(model, cond, new_val_dic): 
            return DBCompiler.Update(model).Set(model, new_val_dic).Where(cond).render()

        @staticmethod
        def insert(model, new_val_dic): # 只插入一条
            values = []
            for k in model._fields:
                if not new_val_dic.has_key(k):
                    raise DBError("not enough args")
                values.append(new_val_dic[k])
                
            return DBCompiler.Insert(model).\
                append("(").All(model).append(")")\
                                      .Values([values])\
                                      .render()


class Executor(object):
    import MySQLdb
    def bind(self, **kwargs):
        self.db = self.MySQLdb.connect(**kwargs)
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
        # model_ins = modelcls()
        # for fname, v in zip(modelcls._fields, ins):
        #     setattr(model_ins, fname, v)
        model_ins = modelcls(**dict(zip(modelcls._fields, ins)))
        model_ins.is_update = True # 表示这个instance是从数据取的，save时是更新而不是新增
        res.append(model_ins)
    return res

if DEBUG:
    from cap import local_dic
else:
    from ..cap import local_dic
def db_bind(**kwargs):
    local_dic.DBexecutor = Executor()
    local_dic.DBexecutor.bind(**kwargs)





if __name__ == "__main__":
    class TestModel(Model):
        field1 = CharField(max_length=22, pk=True)
        f2 = CharField(max_length=253, verbose="yyy")

    db_bind(host="localhost", user="learnguy", passwd="uefgsigw", db="learn")

    print TestModel.query.all()
    len1 = len(TestModel.query.all())
    a = TestModel(field1="test1", f2="test2")
    a.save()
    assert(len(TestModel.query.all()) == len1+1)
    pdb.set_trace()
    a.f2="test2_modify"
    a.save()
    assert(len(TestModel.query.all()) == len1+1)
    import time
    t = time.time()
    TestModel(f2=str(t), field1="shit").save()
    print TestModel.query.all().filter(f2=str(t), field1__contain="shi") 

    
    pdb.set_trace()
    
