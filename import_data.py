import mysql.connector
import pandas as pd

# MySQL connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",              # your MySQL username
    password="438485rr", # your MySQL password
    database="placement_erp"
)
cursor = conn.cursor()

# Function to insert data from CSV into a table
def import_csv_to_mysql(csv_file, table_name, columns):
    df = pd.read_csv(csv_file)
    df.columns = df.columns.str.strip()
    print(df.columns.tolist())
    for _, row in df.iterrows():
        values = tuple(row[col] for col in columns)
        placeholders = ", ".join(["%s"] * len(values))
        sql = f"INSERT IGNORE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        cursor.execute(sql, values)  # <-- Indented inside the loop

    conn.commit()
    print(f" Data from {csv_file} inserted into {table_name}")


# Import students.csv
import_csv_to_mysql(
    "C:\\Users\\joshi\\OneDrive\\Desktop\\AI Powered Placement ERP\\students.csv",  # path to CSV
    "students",
    ["name", "email", "password", "cgpa", "passing_year", "branch", "phone", "skills", "resume_path"]
)

# Import recruiters.csv
import_csv_to_mysql(
    "C:\\Users\\joshi\\OneDrive\\Desktop\\AI Powered Placement ERP\\recruiters.csv",
    "recruiters",
    ["company_name", "email", "phone", "password", "location", "website"]
)
# Import tpos.csv
import_csv_to_mysql(
    "C:\\Users\\joshi\\OneDrive\\Desktop\\AI Powered Placement ERP\\tpos.csv",
    "tpos",
    ["name", "email", "phone", "password"]
)
# Import jobs.csv
import_csv_to_mysql(
    "C:\\Users\\joshi\\OneDrive\\Desktop\\AI Powered Placement ERP\\jobs.csv",
    "jobs",  # <-- Add the table name here
    ["job_id", "company_id", "title", "description", "location", "salary", "deadline", "eligibility_criteria"],
    
)
# Import applications.csv
import_csv_to_mysql(
    "C:\\Users\\joshi\\OneDrive\\Desktop\\AI Powered Placement ERP\\applications.csv",
    "applications",
    ["application_id", "student_id", "job_id", "status", "applied_date"]
)
# Import applications.csv
import_csv_to_mysql(
    "C:\\Users\\joshi\\OneDrive\\Desktop\\AI Powered Placement ERP\\applications.csv",
    "applications",
    ["application_id", "student_id", "job_id", "status", "applied_date"]
)


cursor.close()
conn.close()
