import MySQLdb

db = MySQLdb.connect(
    host='localhost',
    user='learnguy',
    passwd='uefgsigw',
    db='learn'
)
cursor = db.cursor()

cursor.execute("SELECT * FROM people limit 1")

db.commit()

print cursor.fetchall()
