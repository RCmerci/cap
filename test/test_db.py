import sys
sys.path.append("..")
from cap.db import db
import pdb

db.db_bind(host="localhost", user="learnguy", passwd="uefgsigw", db="learn")

class TestModel1(db.Model):
    f1 = db.CharField(max_length=30, verbose="f1")
    f2 = db.IntField(null=True)
    f3 = db.TextField(default="test text")


class TestModel2(db.Model):
    f1 = db.ForeignField(fk=TestModel1)
    f2 = db.DateTimeField(auto_update=True)


try:
    db.create_table(TestModel1)
    db.create_table(TestModel2)
except Exception:
    pass


    
len1 = len(TestModel1.all())
ins1 = TestModel1(f1="f1 test", f2=233)
ins1.save()
len2 = len(TestModel2.all())
ins2 = TestModel2(f1=ins1)
ins2.save()
pdb.set_trace()
assert(len(TestModel1.all())==len1 + 1)
assert(len(TestModel2.all())==len2 + 1)

ins1_1 = TestModel1.all()[-1]
assert(len(ins1_1.TestModel2_set()) == 1)
assert(ins1_1.TestModel2_set()[0].f1._id ==  ins1_1._id)
# -----------------------------------------------------------
class TestModel3(db.Model):
    f1 = db.FloatField(default=2.3333)
    f2 = db.DateTimeField(auto_now=True, auto_update=True)

try:
    db.create_table(TestModel3)
except Exception:
    pass

