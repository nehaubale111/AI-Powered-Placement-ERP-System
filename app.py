# app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
import mysql.connector
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from flask_mail import Mail
from datetime import datetime
from pdfminer.high_level import extract_text as extract_text_from_pdf
from docx import Document as DocxDocument
from pyresparser import ResumeParser
import nltk

# Download required NLTK data
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)

# ==================== APP CONFIGURATION ====================
app = Flask(__name__)
app.secret_key = "secret_key"
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Flask-Mail Configuration
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='your_sending_email@gmail.com',
    MAIL_PASSWORD='your_email_app_password',
    MAIL_DEFAULT_SENDER='your_sending_email@gmail.com'
)
mail = Mail(app)

# ==================== DATABASE CONNECTION ====================
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="438485rr",
        database="placement_erp"
    )

# ==================== DATABASE INITIALIZATION ====================
def ensure_tables_exist():
    """Ensure required tables exist with correct structure"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check and create applications table if it doesn't exist
        cursor.execute("SHOW TABLES LIKE 'applications'")
        applications_table_exists = cursor.fetchone()
        
        if not applications_table_exists:
            cursor.execute("""
                CREATE TABLE applications (
                    application_id INT AUTO_INCREMENT PRIMARY KEY,
                    job_id INT,
                    student_id INT,
                    submitted_resume_path VARCHAR(500),
                    experience_years INT DEFAULT 0,
                    commitment_hours INT DEFAULT 0,
                    applied_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status ENUM('applied', 'shortlisted', 'accepted', 'rejected') DEFAULT 'applied',
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
                )
            """)
            print("Applications table created successfully!")
        else:
            # Check if submitted_resume_path column exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_NAME = 'applications' 
                AND COLUMN_NAME = 'submitted_resume_path'
                AND TABLE_SCHEMA = 'placement_erp'
            """)
            column_exists = cursor.fetchone()[0] > 0
            
            if not column_exists:
                # Add the missing column
                cursor.execute("ALTER TABLE applications ADD COLUMN submitted_resume_path VARCHAR(500)")
                print("Added submitted_resume_path column to applications table!")
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error ensuring tables exist: {e}")

# ==================== RESUME PARSING UTILITIES ====================
def extract_resume_text(file_path):
    """Extract text from PDF or DOCX files"""
    try:
        if file_path.lower().endswith('.pdf'):
            try:
                text = extract_text_from_pdf(file_path)
                if text and text.strip():
                    return text.replace("%", "").replace(":", " ")
            except Exception:
                pass
            
            try:
                from PyPDF2 import PdfReader
                with open(file_path, 'rb') as file:
                    reader = PdfReader(file)
                    text = "".join([page.extract_text() or "" for page in reader.pages])
                    if text.strip():
                        return text
            except Exception:
                pass
                
        elif file_path.lower().endswith(('.docx', '.doc')):
            try:
                doc = DocxDocument(file_path)
                return '\n'.join([p.text for p in doc.paragraphs])
            except Exception:
                return ""
                
        return ""
    except Exception as e:
        app.logger.error(f"Error extracting text: {e}")
        return ""

def simple_text_parsing(text):
    """Parse resume text using regex patterns"""
    import re
    
    if not text:
        return {}
    
    parsed = {}
    
    # Extract contact information
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_match:
        parsed['email'] = email_match.group(0)

    phone_match = re.search(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', text.replace(' ', ''))
    if phone_match:
        parsed['mobile_number'] = phone_match.group(0)

    # Extract name
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines and len(lines[0].split()) <= 4:
        parsed['name'] = lines[0]

    # Extract skills
    common_skills = [
        'python', 'java', 'javascript', 'sql', 'html', 'css', 'c++', 'react', 
        'node.js', 'mongodb', 'mysql', 'php', 'angular', 'vue', 'django', 
        'flask', 'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 
        'opencv', 'computer vision', 'nlp', 'gan', 'predictive analysis', 
        'hugging face', 'aws', 'ec2', 's3', 'langchain', 'faiss'
    ]
    
    found_skills = []
    for skill in common_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', text.lower()):
            found_skills.append(skill)
    
    if found_skills:
        parsed['skills'] = found_skills

    # Extract projects
    projects = []
    project_keywords = {
        'AI-Powered Placement ERP System': 'AI-Powered Placement ERP System with Flask & MySQL',
        'RAG-based PDF Chatbot': 'RAG-based PDF Chatbot with LangChain & Hugging Face'
    }
    
    for keyword, project_name in project_keywords.items():
        if keyword in text:
            projects.append(project_name)
    
    if projects:
        parsed['projects'] = projects

    # Extract certifications
    certs = []
    cert_keywords = ['IIT Kharagpur', 'YHILLS', 'Coursera', 'Forage', 'IEEE']
    for cert in cert_keywords:
        if cert in text:
            certs.append(cert)
    
    if certs:
        parsed['certifications'] = certs

    return parsed

def parse_resume_local(file_path):
    """Main resume parsing function"""
    try:
        text = extract_resume_text(file_path)
        data = simple_text_parsing(text)

        # Fallback to PyResParser if simple parsing fails
        if not data or all(not v for v in data.values() if v not in ([], {})):
            try:
                pyres_data = ResumeParser(file_path).get_extracted_data()
                if pyres_data:
                    data.update(pyres_data)
            except Exception as pyres_error:
                app.logger.error(f"PyResParser failed: {pyres_error}")

        return data if data else {}
    except Exception as e:
        app.logger.error(f"Error in parse_resume_local: {e}")
        return {}

def map_resume_to_profile(parsed_data):
    """Map parsed resume data to student profile fields"""
    mapped = {
        "first_name": None,
        "last_name": None,
        "email": parsed_data.get("email"),
        "phone": parsed_data.get("mobile_number"),
        "department": "AI & ML",
        "tenth_percentage": "95.00",
        "tenth_year": "2020",
        "tenth_board": None,
        "twelfth_percentage": "81.83",
        "twelfth_year": "2022",
        "twelfth_board": None,
        "diploma_percentage": None,
        "diploma_year": None,
        "diploma_branch": None,
        "engg_passing_year": "2026",
        "programming_languages": ", ".join(parsed_data.get("skills", [])),
        "academic_projects": ", ".join(parsed_data.get("projects", [])),
        "certificates": ", ".join(parsed_data.get("certifications", [])),
        "hobbies": None
    }
    
    if parsed_data.get("name"):
        parts = parsed_data["name"].strip().split()
        if len(parts) >= 2:
            mapped["first_name"] = parts[0]
            mapped["last_name"] = " ".join(parts[1:])
        else:
            mapped["first_name"] = parsed_data["name"]
    
    return mapped

# ==================== AUTHENTICATION ROUTES ====================
@app.route("/")
def index():
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        try:
            user = None
            role = None
            
            # Check user type
            cursor.execute("SELECT student_id AS user_id, name, email, password FROM students WHERE email=%s", (email,))
            user = cursor.fetchone()
            if user:
                role = "student"
            else:
                cursor.execute("SELECT company_id AS user_id, company_name AS name, email, password FROM recruiters WHERE email=%s", (email,))
                user = cursor.fetchone()
                if user:
                    role = "recruiter"
                else:
                    cursor.execute("SELECT tpo_id AS user_id, name, email, password FROM tpos WHERE email=%s", (email,))
                    user = cursor.fetchone()
                    if user:
                        role = "tpo"

            if user:
                stored_pw = user.get("password")
                pw_ok = False
                
                # Check password (support both hashed and plain text)
                if stored_pw and (stored_pw.startswith("pbkdf2:") or stored_pw.count("$") >= 2):
                    try:
                        pw_ok = check_password_hash(stored_pw, password)
                    except Exception:
                        pw_ok = False
                else:
                    pw_ok = (stored_pw == password)

                if pw_ok:
                    session["user_id"] = user.get("user_id")
                    session["role"] = role
                    session["email"] = user.get("email")
                    session["name"] = user.get("name")

                    if role == "student":
                        return redirect(url_for("student_dashboard"))
                    elif role == "recruiter":
                        return redirect(url_for("recruiter_dashboard"))
                    elif role == "tpo":
                        return redirect(url_for("tpo_dashboard"))
                else:
                    flash("Invalid email or password.", "error")
            else:
                flash("Invalid email or password.", "error")
                
        finally:
            cursor.close()
            conn.close()

    return render_template("index.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ==================== DASHBOARD ROUTES ====================
@app.route("/student_dashboard")
def student_dashboard():
    if session.get("role") != "student":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    student_id = session.get("user_id")
    profile = {}
    current_resume_path = None
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    try:
        cursor.execute("SELECT * FROM student_profile WHERE student_id=%s", (student_id,))
        profile = cursor.fetchone() or {}
        
        cursor.execute("SELECT resume_path FROM students WHERE student_id=%s", (student_id,))
        r = cursor.fetchone()
        current_resume_path = r["resume_path"] if r else None
        
    finally:
        cursor.close()
        conn.close()
    
    # Merge parsed data with profile
    parsed = session.get('parsed_profile_data', {})
    for k, v in parsed.items():
        if v and (not profile.get(k) or profile.get(k) in ("", None)): 
            profile[k] = v
    
    return render_template("student_dashboard.html", 
                         profile=profile,
                         current_resume_path=current_resume_path,
                         student_name=session.get("name"))

@app.route("/recruiter_dashboard")
def recruiter_dashboard():
    if session.get("role") != "recruiter":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    return render_template("recruiter_dashboard.html")

@app.route("/tpo_dashboard")
def tpo_dashboard():
    if session.get("role") != "tpo":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    return render_template("tpo_dashboard.html")

# ==================== RESUME MANAGEMENT ====================
@app.route("/upload_resume", methods=["POST"])
def upload_resume():
    student_id = session.get("user_id")
    if not student_id: 
        return redirect(url_for("login"))
    
    file = request.files.get("resume")
    if not file or file.filename == "": 
        return redirect(url_for("student_dashboard"))
    
    # Save file
    filename = secure_filename(f"{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file.save(save_path)

    # Parse resume
    parsed = parse_resume_local(save_path)
    mapped = map_resume_to_profile(parsed)
    
    # Store parsed data
    if any(parsed.get(f) for f in ['email', 'mobile_number', 'skills', 'certifications', 'projects']):
        session['parsed_profile_data'] = mapped
        flash("Resume uploaded & parsed!", "success")
    else: 
        flash("Resume uploaded, but limited data parsed.", "warning")
    
    # Update database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE students SET resume_path=%s WHERE student_id=%s", (filename, student_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for("student_dashboard"))

@app.route('/download_resume/<filename>')
def download_resume(filename):
    if session.get("role") not in ["student", "recruiter", "tpo"]: 
        return redirect(url_for("login"))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)

@app.route("/delete_resume", methods=["POST"])
def delete_resume():
    student_id = session.get("user_id")
    if not student_id:
        flash("Unauthorized access.", "error")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT resume_path FROM students WHERE student_id=%s", (student_id,))
        result = cursor.fetchone()

        if result and result[0]:
            old_resume_filename = result[0]
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], old_resume_filename)

            if os.path.exists(file_path):
                os.remove(file_path)

            cursor.execute("UPDATE students SET resume_path=NULL WHERE student_id=%s", (student_id,))
            conn.commit()
            flash("Resume deleted successfully!", "success")
        else:
            flash("No resume found to delete.", "warning")

    except Exception as e:
        conn.rollback()
        app.logger.error(f"Error deleting resume: {e}")
        flash(f"Error deleting resume: {e}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("student_dashboard"))

# ==================== STUDENT PROFILE MANAGEMENT ====================
@app.route("/student/profile", methods=["GET", "POST"])
def student_profile():
    if session.get("role") != "student":
        flash("Access denied.", "error")
        return redirect(url_for("login"))

    student_id = session.get("user_id")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    if request.method == "POST":
        data = request.form.to_dict()
        data["student_id"] = student_id

        # Clean empty values
        for k, v in data.items():
            if v == "":
                data[k] = None

        try:
            cursor.execute("SELECT profile_id FROM student_profile WHERE student_id=%s", (student_id,))
            existing_profile = cursor.fetchone()

            if existing_profile:
                # Update existing profile
                cursor.execute("""
                    UPDATE student_profile SET
                        roll_no=%(roll_no)s, prn_no=%(prn_no)s, department=%(department)s,
                        first_name=%(first_name)s, last_name=%(last_name)s, dob=%(dob)s, gender=%(gender)s,
                        phone=%(phone)s, email=%(email)s,
                        tenth_percentage=%(tenth_percentage)s, tenth_year=%(tenth_year)s, tenth_board=%(tenth_board)s,
                        twelfth_percentage=%(twelfth_percentage)s, twelfth_year=%(twelfth_year)s, twelfth_board=%(twelfth_board)s,
                        diploma_percentage=%(diploma_percentage)s, diploma_year=%(diploma_year)s, diploma_branch=%(diploma_branch)s,
                        sem1=%(sem1)s, sem2=%(sem2)s, sem3=%(sem3)s, sem4=%(sem4)s, sem5=%(sem5)s, sem6=%(sem6)s, sem7=%(sem7)s, sem8=%(sem8)s,
                        average=%(average)s, engg_passing_year=%(engg_passing_year)s, live_backlogs=%(live_backlogs)s, year_gap=%(year_gap)s,
                        extracurricular=%(extracurricular)s, academic_projects=%(academic_projects)s, programming_languages=%(programming_languages)s,
                        certificates=%(certificates)s, hobbies=%(hobbies)s,
                        linkedin_url=%(linkedin_url)s, github_url=%(github_url)s, local_address=%(local_address)s, permanent_address=%(permanent_address)s, native_place=%(native_place)s,
                        last_updated=NOW(), edited_by_student=TRUE
                    WHERE student_id=%(student_id)s
                """, data)
                flash("Profile updated successfully!", "success")
            else:
                # Create new profile
                cursor.execute("""
                    INSERT INTO student_profile (
                        student_id, roll_no, prn_no, department, first_name, last_name, dob, gender, phone, email,
                        tenth_percentage, tenth_year, tenth_board,
                        twelfth_percentage, twelfth_year, twelfth_board,
                        diploma_percentage, diploma_year, diploma_branch,
                        sem1, sem2, sem3, sem4, sem5, sem6, sem7, sem8, average,
                        engg_passing_year, live_backlogs, year_gap,
                        extracurricular, academic_projects, programming_languages, certificates, hobbies,
                        linkedin_url, github_url, local_address, permanent_address, native_place,
                        created_at, edited_by_student
                    ) VALUES (
                        %(student_id)s, %(roll_no)s, %(prn_no)s, %(department)s, %(first_name)s, %(last_name)s, %(dob)s, %(gender)s, %(phone)s, %(email)s,
                        %(tenth_percentage)s, %(tenth_year)s, %(tenth_board)s,
                        %(twelfth_percentage)s, %(twelfth_year)s, %(twelfth_board)s,
                        %(diploma_percentage)s, %(diploma_year)s, %(diploma_branch)s,
                        %(sem1)s, %(sem2)s, %(sem3)s, %(sem4)s, %(sem5)s, %(sem6)s, %(sem7)s, %(sem8)s, %(average)s,
                        %(engg_passing_year)s, %(live_backlogs)s, %(year_gap)s,
                        %(extracurricular)s, %(academic_projects)s, %(programming_languages)s, %(certificates)s, %(hobbies)s,
                        %(linkedin_url)s, %(github_url)s, %(local_address)s, %(permanent_address)s, %(native_place)s,
                        NOW(), FALSE
                    )
                """, data)
                flash("Profile created successfully!", "success")

            conn.commit()
        except Exception as e:
            conn.rollback()
            app.logger.error(f"Error saving profile: {e}")
            flash(f"Error saving profile: {e}", "error")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("student_dashboard"))

    # GET request - load existing profile
    cursor.execute("SELECT * FROM student_profile WHERE student_id=%s", (student_id,))
    profile = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("student_dashboard.html", profile=profile)

# ==================== API ROUTES FOR DATA FETCHING ====================
@app.route("/student_events")
def student_events():
    if session.get("role") != "student":
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.title, e.description, e.date, t.name AS created_by_name
        FROM placement_events e
        LEFT JOIN tpos t ON e.created_by = t.tpo_id
        ORDER BY e.date ASC
    """)
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(events)

@app.route("/prep_resources_student")
def prep_resources_student():
    if session.get("role") != "student":
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.title, r.description, r.file_path, t.name AS created_by_name
        FROM prep_resources r
        LEFT JOIN tpos t ON r.created_by = t.tpo_id
        ORDER BY r.resource_id DESC
    """)
    resources = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(resources)

@app.route('/download_resource/<path:filename>')
def download_resource(filename):
    if session.get("role") not in ["student", "recruiter", "tpo"]:
        return redirect(url_for("login"))
    
    clean_filename = os.path.basename(filename)
    possible_paths = ['static/resources', 'static/uploads', 'resources', 'uploads']
    
    for path in possible_paths:
        file_path = os.path.join(path, clean_filename)
        if os.path.exists(file_path):
            return send_from_directory(path, clean_filename, as_attachment=True)
    
    flash(f"Resource file '{clean_filename}' not found.", "error")
    return redirect(url_for("student_dashboard"))

# ==================== TPO MANAGEMENT ROUTES ====================
@app.route("/add_student", methods=["POST"])
def add_student():
    if session.get("role") != "tpo":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    try:
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        cgpa = request.form.get("cgpa")
        passing_year = request.form.get("passing_year")
        branch = request.form.get("branch")
        phone = request.form.get("phone")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO students (name, email, password, cgpa, passing_year, branch, phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (name, email, password, cgpa, passing_year, branch, phone))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Student added successfully!", "success")
    except Exception as e:
        flash(f"Error adding student: {e}", "error")
    
    return redirect(url_for("tpo_dashboard"))

@app.route("/add_event", methods=["POST"])
def add_event():
    if session.get("role") != "tpo":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    try:
        title = request.form.get("title")
        description = request.form.get("description")
        date = request.form.get("date")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO placement_events (title, description, date, created_by)
            VALUES (%s, %s, %s, %s)
        """, (title, description, date, session.get("user_id")))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Event posted successfully!", "success")
    except Exception as e:
        flash(f"Error posting event: {e}", "error")
    
    return redirect(url_for("tpo_dashboard"))

@app.route("/add_resource", methods=["POST"])
def add_resource():
    if session.get("role") != "tpo":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    try:
        title = request.form.get("title")
        description = request.form.get("description")
        file = request.files.get("file")
        
        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join('static/uploads', filename)
            file.save(save_path)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO prep_resources (title, description, file_path, created_by)
                VALUES (%s, %s, %s, %s)
            """, (title, description, filename, session.get("user_id")))
            conn.commit()
            cursor.close()
            conn.close()
            
            flash("Resource uploaded successfully!", "success")
        else:
            flash("Please select a file.", "error")
            
    except Exception as e:
        flash(f"Error uploading resource: {e}", "error")
    
    return redirect(url_for("tpo_dashboard"))

# ==================== TPO API ROUTES ====================
@app.route('/all_student_profiles')
def all_student_profiles():
    """Get all student profiles for TPO dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT sp.*, s.name as student_name, s.email as student_email, s.resume_path
            FROM student_profile sp
            JOIN students s ON sp.student_id = s.student_id
        """)
        students = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(students)
    except Exception as e:
        app.logger.error(f"Error fetching student profiles: {e}")
        return jsonify([])

@app.route('/all_applications')
def all_applications():
    """Get all job applications for TPO dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if applications table exists
        cursor.execute("SHOW TABLES LIKE 'applications'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            cursor.close()
            conn.close()
            return jsonify([])
        
        cursor.execute("""
            SELECT a.*, s.name as student_name, s.email as student_email
            FROM applications a
            JOIN students s ON a.student_id = s.student_id
            ORDER BY a.applied_date DESC
        """)
        applications = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(applications)
    except Exception as e:
        app.logger.error(f"Error fetching applications: {e}")
        return jsonify([])

@app.route('/all_resources')
def all_resources():
    """Get all preparation resources"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM prep_resources ORDER BY resource_id DESC")
        resources = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(resources)
    except Exception as e:
        app.logger.error(f"Error fetching resources: {e}")
        return jsonify([])

@app.route('/get_student_profile/<int:student_id>')
def get_student_profile(student_id):
    """Get complete profile of a specific student"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM student_profile WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404
            
        return jsonify(student)
        
    except Exception as e:
        app.logger.error(f"Error fetching student profile: {e}")
        return jsonify({'error': 'Failed to fetch student profile'}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route("/delete_student/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            app.logger.info(f"Attempting to delete student with ID: {student_id}")

            # Delete related application details first
            cursor.execute("""
                DELETE FROM application_details 
                WHERE application_id IN (
                    SELECT application_id FROM applications WHERE student_id = %s
                )
            """, (student_id,))

            # Delete applications related to this student
            cursor.execute("DELETE FROM applications WHERE student_id = %s", (student_id,))

            # Delete student profile
            cursor.execute("DELETE FROM student_profile WHERE student_id = %s", (student_id,))

            # Delete student account
            cursor.execute("DELETE FROM students WHERE student_id = %s", (student_id,))

            conn.commit()
            app.logger.info(f"Student {student_id} deleted successfully.")
            return jsonify({"message": "Student and related records deleted successfully."})
    except Exception as e:
        app.logger.error(f"Error deleting student {student_id}: {e}")
        conn.rollback()
        return jsonify({"message": f"Error deleting student: {str(e)}"}), 500
    finally:
        conn.close()


@app.route("/delete_resource/<int:resource_id>", methods=["POST"])
def delete_resource(resource_id):
    """Delete a preparation resource"""
    if session.get("role") != "tpo":
        return jsonify({"error": "Access denied"}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get file path before deleting
        cursor.execute("SELECT file_path FROM prep_resources WHERE resource_id = %s", (resource_id,))
        result = cursor.fetchone()
        
        if result:
            file_path = os.path.join('static/uploads', result[0])
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Delete from database
        cursor.execute("DELETE FROM prep_resources WHERE resource_id = %s", (resource_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Resource deleted successfully"})
    except Exception as e:
        app.logger.error(f"Error deleting resource: {e}")

        return jsonify({"error": str(e)}), 500
    

# ==================== JOB MANAGEMENT ROUTES ====================

@app.route("/post_job", methods=["POST"])
def post_job():
    if session.get("role") != "recruiter":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    try:
        ensure_tables_exist()  # Ensure tables exist before posting job
        
        title = request.form.get("title")
        description = request.form.get("description")
        location = request.form.get("location")
        salary = request.form.get("salary")
        deadline = request.form.get("deadline")
        eligibility_criteria = request.form.get("description", "")  # Using description as fallback
        eligibility = request.form.get("eligibility")  # Minimum CGPA
        target_branches = request.form.getlist("target_branches")  # Multiple branches
        
        # Convert target_branches list to string for storage
        target_branches_str = ",".join(target_branches)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO jobs (company_id, title, description, location, salary, deadline, 
                            eligibility_criteria, eligibility, target_branches)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (session.get("user_id"), title, description, location, salary, deadline, 
              eligibility_criteria, eligibility, target_branches_str))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Job posted successfully!", "success")
    except Exception as e:
        flash(f"Error posting job: {e}", "error")
    
    return redirect(url_for("recruiter_dashboard"))

@app.route("/recruiter_jobs")
def recruiter_jobs():
    if session.get("role") != "recruiter":
        return jsonify([])
    
    try:
        ensure_tables_exist()  # Ensure tables exist before fetching jobs
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT j.*, r.company_name 
            FROM jobs j 
            JOIN recruiters r ON j.company_id = r.company_id 
            WHERE j.company_id = %s 
            ORDER BY j.posted_date DESC
        """, (session.get("user_id"),))
        jobs = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert target_branches string back to list for frontend
        for job in jobs:
            if job['target_branches']:
                job['target_branches'] = job['target_branches'].split(',')
            else:
                job['target_branches'] = ['all']
                
        return jsonify(jobs)
    except Exception as e:
        app.logger.error(f"Error fetching recruiter jobs: {e}")
        return jsonify([])

@app.route("/student_jobs")
def student_jobs():
    """Fetch jobs visible to students based on eligibility and active recruiters."""
    if session.get("role") != "student":
        return jsonify([])

    try:
        ensure_tables_exist()
        student_id = session.get("user_id")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🎓 Get student's branch and CGPA
        cursor.execute("""
            SELECT 
                COALESCE(sp.department, s.branch) AS branch,
                COALESCE(sp.average, s.cgpa, 0) AS cgpa
            FROM students s
            LEFT JOIN student_profile sp ON s.student_id = sp.student_id
            WHERE s.student_id = %s
        """, (student_id,))
        student = cursor.fetchone()

        if not student:
            cursor.close()
            conn.close()
            return jsonify([])

        student_branch = (student["branch"] or "").strip().lower()
        student_cgpa = float(student["cgpa"] or 0.0)

        # 💼 Fetch only active jobs (deadline not passed + active recruiter)
        cursor.execute("""
            SELECT 
                j.job_id, j.title, j.description, j.location, j.salary, j.deadline,
                j.eligibility, j.target_branches, r.company_name, r.status
            FROM jobs j
            JOIN recruiters r ON j.company_id = r.company_id
            WHERE j.deadline >= CURDATE()
              AND (r.status IS NULL OR r.status = 'active')
            ORDER BY j.posted_date DESC
        """)
        all_jobs = cursor.fetchall()

        job_list = []
        for job in all_jobs:
            target_branches = [b.strip().lower() for b in (job["target_branches"] or "").split(",") if b.strip()]
            if not target_branches:
                target_branches = ["all"]

            branch_eligible = (
                "all" in target_branches or 
                any(b in student_branch for b in target_branches)
            )
            cgpa_eligible = student_cgpa >= float(job["eligibility"] or 0.0)
            can_apply = branch_eligible and cgpa_eligible

            job_list.append({
                "job_id": job["job_id"],
                "title": job["title"],
                "description": job["description"],
                "location": job["location"],
                "salary": job["salary"],
                "deadline": job["deadline"].strftime("%Y-%m-%d") if job["deadline"] else None,
                "eligibility": job["eligibility"],
                "target_branches": target_branches,
                "company_name": job["company_name"],
                "branch_eligible": branch_eligible,
                "cgpa_eligible": cgpa_eligible,
                "can_apply": can_apply
            })

        cursor.close()
        conn.close()
        return jsonify(job_list)

    except Exception as e:
        app.logger.error(f"Error fetching student jobs: {e}")
        return jsonify({"error": "Failed to fetch jobs"}), 500

@app.route("/tpo_jobs")
def tpo_jobs():
    if session.get("role") != "tpo":
        return jsonify([])
    
    try:
        ensure_tables_exist()  # Ensure tables exist before fetching jobs
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT j.*, r.company_name 
            FROM jobs j 
            JOIN recruiters r ON j.company_id = r.company_id 
            ORDER BY j.posted_date DESC
        """)
        jobs = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert target_branches string back to list for frontend
        for job in jobs:
            if job['target_branches']:
                job['target_branches'] = job['target_branches'].split(',')
            else:
                job['target_branches'] = ['all']
                
        return jsonify(jobs)
    except Exception as e:
        app.logger.error(f"Error fetching TPO jobs: {e}")
        return jsonify([])

@app.route("/apply_job", methods=["POST"])
def apply_job():
    if session.get("role") != "student":
        return jsonify({"error": "Access denied"}), 403
    
    try:
        ensure_tables_exist()  # Ensure tables exist before applying
        
        job_id = request.form.get("job_id")
        experience_years = request.form.get("experience_years", 0)
        commitment_hours = request.form.get("commitment_hours", 0)
        
        student_id = session.get("user_id")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if student has already applied
        cursor.execute("""
            SELECT * FROM applications 
            WHERE student_id = %s AND job_id = %s
        """, (student_id, job_id))
        
        existing_application = cursor.fetchone()
        if existing_application:
            return jsonify({"error": "You have already applied for this job"}), 400
        
        # Get student's resume path
        cursor.execute("SELECT resume_path FROM students WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()
        resume_path = student['resume_path'] if student else None
        
        if not resume_path:
            return jsonify({"error": "Please upload your resume before applying"}), 400
        
        # Create application
        cursor.execute("""
            INSERT INTO applications (job_id, student_id, submitted_resume_path, 
                                    experience_years, commitment_hours, status)
            VALUES (%s, %s, %s, %s, %s, 'applied')
        """, (job_id, student_id, resume_path, experience_years, commitment_hours))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Application submitted successfully!"})
        
    except Exception as e:
        app.logger.error(f"Error applying for job: {e}")
        return jsonify({"error": "Failed to apply for job"}), 500

@app.route("/recruiter_applicants")
def recruiter_applicants():
    if session.get("role") != "recruiter":
        return jsonify([])
    
    try:
        ensure_tables_exist()  # Ensure tables exist before fetching applicants
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT a.*, j.title as job_title, s.name as student_name, 
                   s.email as student_email, s.branch as student_branch, sp.average as student_cgpa,
                   s.phone as student_phone
            FROM applications a
            JOIN jobs j ON a.job_id = j.job_id
            JOIN students s ON a.student_id = s.student_id
            LEFT JOIN student_profile sp ON s.student_id = sp.student_id
            WHERE j.company_id = %s
            ORDER BY a.applied_date DESC
        """, (session.get("user_id"),))
        
        applications = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(applications)
    except Exception as e:
        app.logger.error(f"Error fetching recruiter applicants: {e}")
        return jsonify([])

@app.route("/update_application", methods=["POST"])
def update_application():
    if session.get("role") != "recruiter":
        return jsonify({"error": "Access denied"}), 403
    
    try:
        ensure_tables_exist()  # Ensure tables exist before updating
        
        application_id = request.form.get("application_id")
        status = request.form.get("status")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE applications 
            SET status = %s 
            WHERE application_id = %s
        """, (status, application_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": f"Application {status} successfully!"})
        
    except Exception as e:
        app.logger.error(f"Error updating application: {e}")
        return jsonify({"error": "Failed to update application"}), 500

@app.route("/delete_job/<int:job_id>", methods=["POST"])
def delete_job(job_id):
    if session.get("role") != "recruiter":
        return jsonify({"error": "Access denied"}), 403
    
    try:
        ensure_tables_exist()  # Ensure tables exist before deleting
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if job belongs to this recruiter
        cursor.execute("SELECT company_id FROM jobs WHERE job_id = %s", (job_id,))
        job = cursor.fetchone()
        
        if not job or job[0] != session.get("user_id"):
            return jsonify({"error": "Job not found or access denied"}), 404
        
        # Delete applications first (due to foreign key constraints)
        cursor.execute("DELETE FROM applications WHERE job_id = %s", (job_id,))
        
        # Delete the job
        cursor.execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Job deleted successfully"})
        
    except Exception as e:
        app.logger.error(f"Error deleting job: {e}")
        return jsonify({"error": "Failed to delete job"}), 500

# ==================== TEST ROUTE ====================
@app.route("/test_recruiter_routes")
def test_recruiter_routes():
    """Test route to check if recruiter routes are working"""
    if session.get("role") != "recruiter":
        return jsonify({"error": "Access denied"}), 403
    
    try:
        ensure_tables_exist()
        
        # Test jobs table access
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as count FROM jobs WHERE company_id = %s", (session.get("user_id"),))
        job_count = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as count FROM applications a JOIN jobs j ON a.job_id = j.job_id WHERE j.company_id = %s", (session.get("user_id"),))
        app_count = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "jobs_count": job_count['count'],
            "applications_count": app_count['count'],
            "message": "Recruiter routes are working correctly"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== UTILITY ROUTES ====================
@app.route("/about")
def about(): 
    return render_template("about.html")

@app.route("/contact")
def contact(): 
    return render_template("contact.html")

# In app.py
@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)