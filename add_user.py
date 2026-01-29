import sqlite3
from passlib.hash import argon2
import os

# هذا المسار لقاعدة البيانات على Render
db_path = os.path.join(os.getcwd(), "lab.db")  # لا تغير الاسم، هو نفس اسم الملف في المشروع على Render

username = "admin2"
password = "1234"
role = "admin"

hashed = argon2.hash(password)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT * FROM users WHERE username=?", (username,))
if cursor.fetchone():
    print(f"User '{username}' already exists!")
else:
    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        (username, hashed, role)
    )
    conn.commit()
    print(f"User '{username}' added successfully!")

conn.close()
