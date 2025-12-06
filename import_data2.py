import mysql.connector

# MySQL connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",              # your MySQL username
    password="438485rr", # your MySQL password
    database="placement_erp"
)
cursor = conn.cursor()

# Insert users from students
cursor.execute("""
    INSERT IGNORE INTO users (email, password, role)
    SELECT email, password, 'student' FROM students;
""")

# Insert users from recruiters
cursor.execute("""
    INSERT IGNORE INTO users (email, password, role)
    SELECT email, password, 'recruiter' FROM recruiters;
""")

# Insert users from tpos
cursor.execute("""
    INSERT IGNORE INTO users (email, password, role)
    SELECT email, password, 'tpo' FROM tpos;
""")

conn.commit()
print("Users table populated from students, recruiters, and tpos")

cursor.close()
conn.close()
