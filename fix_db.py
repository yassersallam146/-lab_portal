import sqlite3

# افتح قاعدة البيانات
conn = sqlite3.connect("lab.db")
cursor = conn.cursor()

# احذف أي صف سبب مشاكل (مثلاً admin2)
cursor.execute("DELETE FROM users WHERE username='admin2'")

conn.commit()
conn.close()
print("Problematic user removed, DB fixed!")
