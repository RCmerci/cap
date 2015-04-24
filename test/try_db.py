import MySQLdb

db = MySQLdb.connect(
    host='107.170.196.218',
    user='root',
    password='uefgsigw',
    db='learn'
)
cursor = db.cursor()

cursor.execute("SELECT * FROM people")

db.commit()
