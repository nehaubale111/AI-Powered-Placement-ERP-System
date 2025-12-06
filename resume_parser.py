import pdfplumber
import docx2txt
import re
import mysql.connector

# ===============================
# Extract Text from Resume
# ===============================
def extract_text(file_path):
    text = ""
    if file_path.endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    elif file_path.endswith(".docx"):
        text = docx2txt.process(file_path)
    return text

# ===============================
# Parse Resume Data
# ===============================
def parse_resume(text):
    data = {}

    # Email
    email = re.search(r'[\w\.-]+@[\w\.-]+', text)
    if email:
        data["email"] = email.group(0)

    # Phone
    phone = re.search(r'\b\d{10}\b', text)
    if phone:
        data["phone"] = phone.group(0)

    # Skills
    skills_list = [
        "Python", "Java", "C++", "C", "SQL", "HTML", "CSS", "JavaScript",
        "Machine Learning", "Deep Learning", "AI", "NLP", "Flask", "Django",
        "Data Science", "React", "Node.js"
    ]
    found_skills = [s for s in skills_list if s.lower() in text.lower()]
    data["skills"] = ", ".join(found_skills)

    return data

# ===============================
# Save Parsed Data into MySQL
# ===============================
def save_to_mysql(student_id, data, resume_path):
    conn = mysql.connector.connect(
        host="localhost", user="root", password="438485rr", database="placement_erp"
    )
    cursor = conn.cursor()

    sql = """UPDATE students 
             SET email=%s, phone=%s, skills=%s, resume_path=%s
             WHERE student_id=%s"""
    cursor.execute(sql, (
        data.get("email"),
        data.get("phone"),
        data.get("skills"),
        resume_path,
        student_id
    ))

    conn.commit()
    conn.close()
