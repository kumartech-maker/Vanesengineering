from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from datetime import datetime
import sqlite3
import os
import pandas as pd
import math
from num2words import num2words
import csv
from io import StringIO
from flask import Response, send_file

app = Flask(__name__)
app.secret_key = 'secretkey'

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_db_connection():
    return get_db()

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            contact TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gst TEXT,
            address TEXT,
            bank_name TEXT,
            account_number TEXT,
            ifsc TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS vendor_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            name TEXT,
            phone TEXT,
            email TEXT,
            FOREIGN KEY(vendor_id) REFERENCES vendors(id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT,
            name TEXT,
            gender TEXT,
            dob TEXT,
            blood_group TEXT,
            department TEXT,
            designation TEXT,
            contact TEXT,
            phone TEXT,
            email TEXT,
            join_date TEXT,
            address TEXT,
            role TEXT,
            photo_filename TEXT,
            password TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS employee_logins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enquiry_id TEXT,
            project_code TEXT,
            vendor_id INTEGER,
            quotation_ro TEXT,
            location TEXT,
            contact_number TEXT,
            email TEXT,
            start_date TEXT,
            end_date TEXT,
            incharge TEXT,
            status TEXT DEFAULT 'new',
            notes TEXT,
            file_name TEXT,
            total_sqm REAL DEFAULT 0,
            FOREIGN KEY(vendor_id) REFERENCES vendors(id)
        )
    ''')


    cur.execute('''
        CREATE TABLE IF NOT EXISTS duct_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            duct_no TEXT,
            duct_type TEXT,
            factor TEXT,
            width1 REAL,
            height1 REAL,
            width2 REAL,
            height2 REAL,
            length_or_radius REAL,
            quantity INTEGER,
            degree_or_offset TEXT,
            gauge TEXT,
            area REAL DEFAULT 0,
            nuts_bolts TEXT,
            cleat TEXT,
            gasket TEXT,
            corner_pieces TEXT,
            weight REAL DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    cur.execute("DROP TABLE IF EXISTS production_progress")
    cur.execute('''
        CREATE TABLE production_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            sheet_cutting_sqm REAL DEFAULT 0,
            plasma_fabrication_sqm REAL DEFAULT 0,
            boxing_assembly_sqm REAL DEFAULT 0,
            quality_check_pct REAL DEFAULT 0,
            dispatch_percent REAL DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT DEFAULT 'Absent',
            check_in TEXT,
            check_out TEXT,
            FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
        )
    ''')

    cur.execute("""
        CREATE TABLE IF NOT EXISTS summary_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            diagram TEXT,
            area_24g REAL DEFAULT 0,
            area_22g REAL DEFAULT 0,
            area_20g REAL DEFAULT 0,
            area_18g REAL DEFAULT 0,
            sheet_cutting REAL DEFAULT 0,
            plasma_fabrication REAL DEFAULT 0,
            boxing_assembly REAL DEFAULT 0,
            quality_checking REAL DEFAULT 0,
            dispatch REAL DEFAULT 0,
            overall_progress REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute('''
        INSERT OR IGNORE INTO summary_reports (
            project_id, diagram,
            area_24g, area_22g, area_20g, area_18g,
            sheet_cutting, plasma_fabrication, boxing_assembly,
            quality_checking, dispatch, overall_progress
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        'A-123', 'diagram1.jpg', 150.0, 120.0, 80.0, 60.0,
        45.0, 40.0, 35.0, 30.0, 20.0, 60.0
    ))

    dummy_employees = [
        ('VE/EMP/0001', 'Madhan Kumar', 'Engineer', '9876543210', 'madhan@example.com', 'default.jpg', '2023-06-01'),
        ('VE/EMP/0002', 'Rajesh K', 'Supervisor', '9876543211', 'rajesh@example.com', 'default.jpg', '2023-07-10'),
        ('VE/EMP/0003', 'Priya R', 'Designer', '9876543212', 'priya@example.com', 'default.jpg', '2024-01-15')
    ]
    for emp in dummy_employees:
        cur.execute('''
            INSERT OR IGNORE INTO employees (emp_id, name, role, phone, email, photo_filename, join_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', emp)

    today = datetime.today().strftime('%Y-%m-%d')
    dummy_attendance = [
        ('VE/EMP/0001', today, 'Present', '09:00', '18:00'),
        ('VE/EMP/0002', today, 'Absent', '', ''),
        ('VE/EMP/0003', today, 'Present', '09:15', '17:45')
    ]
    for record in dummy_attendance:
        cur.execute('''
            INSERT INTO attendance (emp_id, date, status, check_in, check_out)
            VALUES (?, ?, ?, ?, ?)
        ''', record)

    cur.execute('''
        INSERT OR IGNORE INTO users (email, name, role, contact, password)
        VALUES (?, ?, ?, ?, ?)
    ''', ("admin@ducting.com", "Admin", "Admin", "9999999999", "admin123"))

    cur.execute('''
        INSERT OR IGNORE INTO vendors (id, name, gst, address, bank_name, account_number, ifsc)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (1, "Dummy Vendor Pvt Ltd", "29ABCDE1234F2Z5", "123 Main Street, City", "Axis Bank", "1234567890", "UTIB0000123"))

    cur.execute('''
        INSERT OR IGNORE INTO vendor_contacts (vendor_id, name, phone, email)
        VALUES (?, ?, ?, ?)
    ''', (1, "Mr. Dummy", "9876543210", "dummy@vendor.com"))

    conn.commit()
    conn.close()

@app.before_request
def setup_db_on_request():
    init_db()

users_db = [
    {"name": "MD User", "email": "md@company.com", "password": "md123", "role": "md"},
    {"name": "Project Manager", "email": "pm@company.com", "password": "pm123", "role": "pm"},
    {"name": "Design Engineer", "email": "de@company.com", "password": "de123", "role": "de"}
]

#---------- ✅ Login ----------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # 🔍 Search in mock database  
        user = next((u for u in users_db if u['email'] == email and u['password'] == password), None)

        if user:
            session['user'] = user['name']
            session['role'] = user['role']
            flash("✅ Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("❌ Invalid credentials!", "danger")
            return redirect(url_for('login'))

    return render_template("login.html")




# ---------- ✅ Logout ----------

@app.route('/logout')
def logout():
    session.clear()
    flash("🔒 You have been logged out.", "success")
    return redirect(url_for('login'))

# ---------- ✅ Dashboard ----------

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template("dashboard.html", user=session['user'])


@app.route("/setup_db")
def setup_db():
    conn = get_db()
    cur = conn.cursor()

    # Check and add missing columns safely
    def add_column_if_missing(column_name, column_def):
        try:
            cur.execute(f"ALTER TABLE production_progress ADD COLUMN {column_name} {column_def}")
            print(f"✅ Added column: {column_name}")
        except sqlite3.OperationalError as e:
            if f"duplicate column name: {column_name}" in str(e).lower():
                print(f"⚠️ Column already exists: {column_name}")
            else:
                print(f"❌ Error adding column {column_name}: {e}")

    add_column_if_missing("quality_check_percent", "REAL DEFAULT 0")
    add_column_if_missing("dispatch_percent", "REAL DEFAULT 0")

    conn.commit()
    conn.close()
    return "✅ Database setup complete!"

# ---------- ✅ Vendor Registration ----------

@app.route('/vendor_registration', methods=['GET', 'POST'])
def vendor_registration():
    if request.method == 'POST':
        vendor_name = request.form['vendor_name']
        gst = request.form['gst']
        address = request.form['address']
        bank_name = request.form['bank_name']
        account_number = request.form['account_number']
        ifsc = request.form['ifsc']

        contacts = []
        for i in range(len(request.form.getlist('contact_name'))):
            contacts.append({
                'name': request.form.getlist('contact_name')[i],
                'phone': request.form.getlist('contact_phone')[i],
                'email': request.form.getlist('contact_email')[i],
            })

        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO vendors (name, gst, address, bank_name, account_number, ifsc) VALUES (?, ?, ?, ?, ?, ?)",
                    (vendor_name, gst, address, bank_name, account_number, ifsc))
        vendor_id = cur.lastrowid

        for contact in contacts:
            cur.execute("INSERT INTO vendor_contacts (vendor_id, name, phone, email) VALUES (?, ?, ?, ?)",
                        (vendor_id, contact['name'], contact['phone'], contact['email']))

        conn.commit()
        conn.close()
        flash("✅ Vendor registered successfully!", "success")
        return redirect(url_for('vendor_registration'))

    return render_template('vendor_registration.html')

# ---------- ✅ API: Get Vendor Info (For Auto-Fill) ----------

@app.route('/api/vendor/<int:vendor_id>')
def get_vendor_info(vendor_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT gst, address FROM vendors WHERE id = ?", (vendor_id,))
    vendor = cur.fetchone()

    if vendor:
        return jsonify({'gst': vendor['gst'], 'address': vendor['address']})
    else:
        return jsonify({}), 404



# ---------- ✅ View All Projects ----------
@app.route('/projects')
def projects():
    conn = get_db()
    cur = conn.cursor()

    # Fetch all projects with their associated vendor names
    cur.execute("""
        SELECT p.*, v.name AS vendor_name
        FROM projects p
        LEFT JOIN vendors v ON p.vendor_id = v.id
        ORDER BY p.id DESC
    """)
    projects = cur.fetchall()

    # Fetch all vendors to populate dropdowns
    cur.execute("SELECT * FROM vendors ORDER BY id DESC")
    vendors = cur.fetchall()

    conn.close()

    # Default selected project (first one in list, if available)
    selected_project = projects[0] if projects else None

    # Generate unique enquiry ID using timestamp
    enquiry_id = "ENQ" + datetime.now().strftime("%Y%m%d%H%M%S")

    return render_template('projects.html',
                           projects=projects,
                           vendors=vendors,
                           project=selected_project,
                           enquiry_id=enquiry_id)


@app.route('/project/edit/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        project_code = request.form['project_code']
        vendor_id = request.form['vendor_id']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        location = request.form['location']
        incharge = request.form['incharge']
        notes = request.form['notes']
        enquiry_id = request.form['enquiry_id']
        client_name = request.form['client_name']
        site_location = request.form['site_location']
        engineer_name = request.form['engineer_name']
        mobile = request.form['mobile']
        email = request.form.get('email')  # Optional
        status = request.form['status']
        total_sqm = request.form.get('total_sqm', 0)

        cur.execute('''
            UPDATE projects SET
                project_code = ?, vendor_id = ?, start_date = ?, end_date = ?,
                location = ?, incharge = ?, notes = ?, enquiry_id = ?,
                client_name = ?, site_location = ?, engineer_name = ?, mobile = ?,
                email = ?, status = ?, total_sqm = ?
            WHERE id = ?
        ''', (
            project_code, vendor_id, start_date, end_date, location, incharge,
            notes, enquiry_id, client_name, site_location, engineer_name, mobile,
            email, status, total_sqm, project_id
        ))

        conn.commit()
        conn.close()
        return redirect(url_for('projects'))

    # GET: Load current project + vendor list
    cur.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    project = cur.fetchone()

    cur.execute('SELECT * FROM vendors ORDER BY id DESC')
    vendors = cur.fetchall()

    conn.close()
    return render_template('edit_project.html', project=project, vendors=vendors)


# ---------- ✅ Create Project ----------
@app.route('/create_project', methods=['POST'])
def create_project():
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        project_name = request.form.get('project_name')
        vendor_id = request.form.get('vendor_id')
        quotation_ro = request.form.get('quotation_ro')
        location = request.form.get('location')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        incharge = request.form.get('incharge')
        contact_number = request.form.get('contact_number')
        email = request.form.get('email')
        notes = request.form.get('notes')
        status = "pending"

        # Handle drawing file
        drawing_file = request.files.get('drawing_file')
        drawing_filename = None
        if drawing_file and drawing_file.filename:
            drawing_filename = secure_filename(drawing_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], drawing_filename)
            drawing_file.save(file_path)

        # DB Insert
        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO projects 
            (client_name, vendor_id, quotation_ro, location, start_date, end_date,
             incharge, contact_number, email, notes, drawing_file, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_name, vendor_id, quotation_ro, location, start_date, end_date,
            incharge, contact_number, email, notes, drawing_filename, status
        ))
        conn.commit()

        # Generate and update Enquiry ID
        project_id = cur.lastrowid
        enquiry_id = f"ENQ-{str(project_id).zfill(4)}"
        cur.execute("UPDATE projects SET enquiry_id = ? WHERE id = ?", (enquiry_id, project_id))
        conn.commit()

        conn.close()
        flash("✅ Project created successfully.", "success")
        return redirect(url_for('projects'))

    except Exception as e:
        print("❌ Error creating project:", e)
        flash("❌ Failed to create project.", "danger")
        return redirect(url_for('projects'))
# ---------- ✅ Add Measurement Info to Project ----------

@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    project_id = request.form['project_id']
    client_name = request.form['client_name']
    site_location = request.form['site_location']
    engineer_name = request.form['engineer_name']
    mobile = request.form['mobile']

    conn = get_db()
    cur = conn.cursor()

    # Update basic project info and move project to "preparation" status
    cur.execute('''
        UPDATE projects SET
            client_name = ?, 
            site_location = ?, 
            engineer_name = ?, 
            mobile = ?, 
            status = ?
        WHERE id = ?
    ''', (
        client_name, site_location, engineer_name, mobile, 'preparation', project_id
    ))

    conn.commit()
    conn.close()
    return '', 200

# ---------- ✅ Open Specific Project and Duct Entries ----------
@app.route('/project/<int:project_id>')
def open_project(project_id):
    conn = get_db()
    cur = conn.cursor()

    # ✅ Get selected project with vendor name
    cur.execute("""
        SELECT p.*, v.name as vendor_name
        FROM projects p
        LEFT JOIN vendors v ON p.vendor_id = v.id
        WHERE p.id = ?
    """, (project_id,))
    project = cur.fetchone()

    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('projects'))

    # ✅ All projects for the left-side list
    cur.execute("""
        SELECT p.*, v.name as vendor_name
        FROM projects p
        LEFT JOIN vendors v ON p.vendor_id = v.id
        ORDER BY p.id DESC
    """)
    projects = cur.fetchall()

    # ✅ All vendors for dropdown
    cur.execute("SELECT * FROM vendors")
    vendors = cur.fetchall()

    # ✅ Duct entries linked to this project
    cur.execute("SELECT * FROM duct_entries WHERE project_id = ?", (project_id,))
    duct_rows = cur.fetchall()

    # ✅ Totals calculation
    ducts = []
    total_area = total_nuts = total_cleat = total_gasket = total_corner = total_weight = 0.0
    gauge_area_totals = {"24G": 0.0, "22G": 0.0, "20G": 0.0, "18G": 0.0}

    for row in duct_rows:
        d = dict(row)
        area = float(d.get('area') or 0)
        nuts = float(d.get('nuts_bolts') or 0)
        cleat = float(d.get('cleat') or 0)
        gasket = float(d.get('gasket') or 0)
        corner = float(d.get('corner_pieces') or 0)
        weight = float(d.get('weight') or 0)
        gauge = (d.get('gauge') or '').strip()

        # Totals
        total_area += area
        total_nuts += nuts
        total_cleat += cleat
        total_gasket += gasket
        total_corner += corner
        total_weight += weight

        # Area by gauge
        if gauge in gauge_area_totals:
            gauge_area_totals[gauge] += area

        # Add parsed values to row
        d.update({
            'area': area,
            'nuts_bolts': nuts,
            'cleat': cleat,
            'gasket': gasket,
            'corner_pieces': corner,
            'weight': weight
        })
        ducts.append(d)

    conn.close()

    return render_template("projects.html",
                           project=project,
                           projects=projects,
                           vendors=vendors,
                           ducts=ducts,
                           total_area=round(total_area, 2),
                           total_nuts=round(total_nuts, 2),
                           total_cleat=round(total_cleat, 2),
                           total_gasket=round(total_gasket, 2),
                           total_corner=round(total_corner, 2),
                           total_weight=round(total_weight, 2),
                           gauge_area_totals=gauge_area_totals)

# ---------- ✅ Add Duct Entry ----------

@app.route('/add_duct', methods=['POST'])
def add_duct():
    import math
    project_id = request.form['project_id']
    duct_no = request.form['duct_no']
    duct_type = request.form['duct_type'].upper()
    w1 = float(request.form.get('width1') or 0)
    h1 = float(request.form.get('height1') or 0)
    w2 = float(request.form.get('width2') or 0)
    h2 = float(request.form.get('height2') or 0)
    qty = int(request.form.get('quantity') or 0)
    length = float(request.form.get('length_or_radius') or 0)
    deg = float(request.form.get('degree_or_offset') or 0)
    factor = float(request.form.get('factor') or 1.0)

    # 🧮 Area calculation
    area = 0
    if duct_type == 'ST':
        area = 2 * (w1 + h1) / 1000 * (length / 1000) * qty
    elif duct_type == 'RED':
        area = (w1 + h1 + w2 + h2) / 1000 * (length / 1000) * qty * factor
    elif duct_type == 'DUM':
        area = (w1 * h1) / 1000000 * qty
    elif duct_type == 'OFFSET':
        area = (w1 + h1 + w2 + h2) / 1000 * ((length + deg) / 1000) * qty * factor
    elif duct_type == 'SHOE':
        area = (w1 + h1) * 2 / 1000 * (length / 1000) * qty * factor
    elif duct_type == 'VANES':
        area = w1 / 1000 * (2 * math.pi * (w1 / 1000) / 4) * qty
    elif duct_type == 'ELB':
        area = 2 * (w1 + h1) / 1000 * ((h1 / 2 / 1000) + (length / 1000) * (math.pi * (deg / 180))) * qty * factor

    # 🧮 Determine gauge
    gauge = '18g'
    if w1 <= 751 and h1 <= 751:
        gauge = '24g'
    elif w1 <= 1201 and h1 <= 1201:
        gauge = '22g'
    elif w1 <= 1800 and h1 <= 1800:
        gauge = '20g'

    # 🧮 Material calculations
    nuts_bolts = qty * 4
    cleat_factor = {'24g': 4, '22g': 8, '20g': 10}.get(gauge, 12)
    cleat = qty * cleat_factor
    gasket = (w1 + h1 + w2 + h2) / 1000 * qty
    corner_pieces = 0 if duct_type == 'DUM' else qty * 8

    # 🧮 Weight (example values per m²)
    weight_per_m2 = {'24g': 4.0, '22g': 5.0, '20g': 6.0, '18g': 7.5}
    weight = area * weight_per_m2.get(gauge, 7.5)

    # ✅ Insert to DB
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO duct_entries (
            project_id, duct_no, duct_type, width1, height1, width2, height2,
            quantity, length_or_radius, degree_or_offset, factor,
            area, gauge, nuts_bolts, cleat, gasket, corner_pieces, weight
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        project_id, duct_no, duct_type, w1, h1, w2, h2,
        qty, length, deg, factor,
        round(area, 2), gauge, round(nuts_bolts, 2), round(cleat, 2),
        round(gasket, 2), round(corner_pieces, 2), round(weight, 2)
    ))
    conn.commit()
    conn.close()

    flash("✅ Duct entry added successfully!", "success")
    return redirect(url_for('open_project', project_id=project_id))

# ---------- ✅ Edit Duct Entry ----------

@app.route("/edit_duct/<int:entry_id>", methods=["GET", "POST"])
def get_entry(entry_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 🔎 Fetch the duct entry to edit
    cur.execute("SELECT * FROM duct_entries WHERE id = ?", (entry_id,))
    entry = cur.fetchone()
    if not entry:
        flash("Entry not found", "danger")
        return redirect(url_for("projects"))

    project_id = entry["project_id"]

    # 📝 Form Submission
    if request.method == "POST":
        data = {
            "duct_no": request.form.get("duct_no"),
            "duct_type": request.form.get("duct_type"),
            "width1": request.form.get("width1"),
            "height1": request.form.get("height1"),
            "width2": request.form.get("width2"),
            "height2": request.form.get("height2"),
            "length_or_radius": request.form.get("length_or_radius"),
            "degree_or_offset": request.form.get("degree_or_offset"),
            "quantity": request.form.get("quantity"),
            "gauge": request.form.get("gauge"),
            "factor": request.form.get("factor"),
            "area": request.form.get("area"),
            "nuts_bolts": request.form.get("nuts_bolts"),
            "cleat": request.form.get("cleat"),
            "gasket": request.form.get("gasket"),
            "corner_pieces": request.form.get("corner_pieces")
        }

        # ✅ Update the duct entry
        cur.execute("""
            UPDATE duct_entries SET
                duct_no = :duct_no,
                duct_type = :duct_type,
                width1 = :width1,
                height1 = :height1,
                width2 = :width2,
                height2 = :height2,
                length_or_radius = :length_or_radius,
                degree_or_offset = :degree_or_offset,
                quantity = :quantity,
                gauge = :gauge,
                factor = :factor,
                area = :area,
                nuts_bolts = :nuts_bolts,
                cleat = :cleat,
                gasket = :gasket,
                corner_pieces = :corner_pieces
            WHERE id = :entry_id
        """, {**data, "entry_id": entry_id})

        conn.commit()
        conn.close()
        flash("✅ Entry updated successfully", "success")
        return redirect(url_for('open_project', project_id=project_id))

    # ⏪ Re-render edit page if GET method
    cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cur.fetchone()

    cur.execute("SELECT * FROM vendors")
    vendors = cur.fetchall()

    cur.execute("SELECT * FROM duct_entries WHERE project_id = ?", (project_id,))
    entries = cur.fetchall()

    # 📊 Totals
    def safe_float(val): return float(val or 0)

    total_area = sum(safe_float(d['area']) for d in entries)
    total_nuts = sum(safe_float(d['nuts_bolts']) for d in entries)
    total_cleat = sum(safe_float(d['cleat']) for d in entries)
    total_gasket = sum(safe_float(d['gasket']) for d in entries)
    total_corner = sum(safe_float(d['corner_pieces']) for d in entries)

    conn.close()

    # 📤 Render with pre-filled edit form
    return render_template("projects.html",
                           project=project,
                           vendors=vendors,
                           entries=entries,
                           edit_entry=entry,
                           total_area=round(total_area, 2),
                           total_nuts=round(total_nuts, 2),
                           total_cleat=round(total_cleat, 2),
                           total_gasket=round(total_gasket, 2),
                           total_corner=round(total_corner, 2))

# ---------- ✅ Update Duct Entry (Recalculate Area) ----------

@app.route("/update_duct/<int:entry_id>", methods=["POST"])
def update_duct(entry_id):
    import math
    conn = get_db()
    cur = conn.cursor()

    # Fetch project ID
    cur.execute("SELECT project_id FROM duct_entries WHERE id = ?", (entry_id,))
    row = cur.fetchone()
    if not row:
        flash("Entry not found", "danger")
        return redirect(url_for("projects"))
    project_id = row[0]

    # Read updated values
    duct_no = request.form["duct_no"]
    duct_type = request.form["duct_type"].upper()
    w1 = float(request.form.get("width1") or 0)
    h1 = float(request.form.get("height1") or 0)
    w2 = float(request.form.get("width2") or 0)
    h2 = float(request.form.get("height2") or 0)
    qty = int(request.form.get("quantity") or 0)
    length = float(request.form.get("length_or_radius") or 0)
    deg = float(request.form.get("degree_or_offset") or 0)
    factor = float(request.form.get("factor") or 1.0)

    # Recalculate area
    area = 0
    if duct_type == 'ST':
        area = 2 * (w1 + h1) / 1000 * (length / 1000) * qty
    elif duct_type == 'RED':
        area = (w1 + h1 + w2 + h2) / 1000 * (length / 1000) * qty * factor
    elif duct_type == 'DUM':
        area = (w1 * h1) / 1000000 * qty
    elif duct_type == 'OFFSET':
        area = (w1 + h1 + w2 + h2) / 1000 * ((length + deg) / 1000) * qty * factor
    elif duct_type == 'SHOE':
        area = (w1 + h1) * 2 / 1000 * (length / 1000) * qty * factor
    elif duct_type == 'VANES':
        area = w1 / 1000 * (2 * math.pi * (w1 / 1000) / 4) * qty
    elif duct_type == 'ELB':
        area = 2 * (w1 + h1) / 1000 * ((h1 / 2 / 1000) + (length / 1000) * (math.pi * (deg / 180))) * qty * factor

    # Determine gauge
    gauge = '18g'
    if w1 <= 751 and h1 <= 751:
        gauge = '24g'
    elif w1 <= 1201 and h1 <= 1201:
        gauge = '22g'
    elif w1 <= 1800 and h1 <= 1800:
        gauge = '20g'

    nuts_bolts = qty * 4
    cleat_factor = 12
    if gauge == '24g':
        cleat_factor = 4
    elif gauge == '22g':
        cleat_factor = 8
    elif gauge == '20g':
        cleat_factor = 10
    cleat = qty * cleat_factor
    gasket = (w1 + h1 + w2 + h2) / 1000 * qty
    corner_pieces = 0 if duct_type == 'DUM' else qty * 8

    # Update record
    cur.execute("""
        UPDATE duct_entries SET
            duct_no = ?, duct_type = ?, width1 = ?, height1 = ?, width2 = ?, height2 = ?,
            quantity = ?, length_or_radius = ?, degree_or_offset = ?, factor = ?,
            area = ?, gauge = ?, nuts_bolts = ?, cleat = ?, gasket = ?, corner_pieces = ?
        WHERE id = ?
    """, (
        duct_no, duct_type, w1, h1, w2, h2,
        qty, length, deg, factor,
        round(area, 2), gauge, round(nuts_bolts, 2), round(cleat, 2),
        round(gasket, 2), round(corner_pieces, 2),
        entry_id
    ))
    conn.commit()
    conn.close()

    flash("✅ Duct entry updated", "success")
    return redirect(url_for("open_project", project_id=project_id))

# ---------- ✅ Delete Duct Entry ----------

@app.route("/delete_duct/<int:entry_id>", methods=["POST"])
def delete_duct(entry_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT project_id FROM duct_entries WHERE id = ?", (entry_id,))
    row = cur.fetchone()
    if not row:
        flash("Entry not found", "danger")
        return redirect(url_for("projects"))
    project_id = row[0]

    cur.execute("DELETE FROM duct_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

    flash("🗑️ Duct entry deleted", "success")
    return redirect(url_for("open_project", project_id=project_id))

# ---------- ✅ Export PDF ----------
@app.route('/export_pdf/<int:project_id>')
def export_pdf(project_id):
    from flask import send_file
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    from io import BytesIO
    import os
    import sqlite3

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Project Info
    c.execute("SELECT client_name, site_location FROM projects WHERE id = ?", (project_id,))
    proj = c.fetchone()
    client_name, site_location = proj if proj else ("", "")

    # Logo and Heading
    logo_path = os.path.join("static", "logo.png")
    if os.path.exists(logo_path):
        p.drawImage(logo_path, 40, height - 80, width=80, preserveAspectRatio=True)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(150, height - 50, "Vanes Engineering Pvt Ltd")
    p.setFont("Helvetica", 9)
    p.drawString(150, height - 65, "Ducting Live Table Export")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, height - 95, f"Client: {client_name}")
    p.drawString(350, height - 95, f"Site: {site_location}")

    # Headers for Live Table
    headers = ["Duct No", "Type", "W1", "H1", "W2", "H2", "Qty", "Len", "Deg", "Factor", "Gauge",
               "Area", "24G", "22G", "20G", "18G", "Nuts", "Cleat", "Gasket", "Corner", "Weight"]

    fields = ["duct_no", "duct_type", "width1", "height1", "width2", "height2", "quantity",
              "length_or_radius", "degree_or_offset", "factor", "gauge", "area",
              "nuts_bolts", "cleat", "gasket", "corner_pieces", "weight"]

    # Fetch duct entries
    c.execute(f"SELECT {','.join(fields)} FROM duct_entries WHERE project_id = ?", (project_id,))
    rows = c.fetchall()
    conn.close()

    data = [headers]
    totals = {key: 0 for key in ["area", "24G", "22G", "20G", "18G", "quantity", "weight"]}

    for row in rows:
        row_dict = dict(zip(fields, row))
        area = row_dict.get("area", 0) or 0
        gauge = (row_dict.get("gauge") or "").strip()

        # Gauge-specific area split
        g24 = area if gauge == "24G" else 0
        g22 = area if gauge == "22G" else 0
        g20 = area if gauge == "20G" else 0
        g18 = area if gauge == "18G" else 0

        # Format each row
        formatted_row = [
            row_dict.get("duct_no", ""),
            row_dict.get("duct_type", ""),
            round(row_dict.get("width1", 0), 2),
            round(row_dict.get("height1", 0), 2),
            round(row_dict.get("width2", 0), 2),
            round(row_dict.get("height2", 0), 2),
            row_dict.get("quantity", ""),
            round(row_dict.get("length_or_radius", 0), 2),
            row_dict.get("degree_or_offset", ""),
            row_dict.get("factor", ""),
            row_dict.get("gauge", ""),
            round(area, 2),
            round(g24, 2),
            round(g22, 2),
            round(g20, 2),
            round(g18, 2),
            row_dict.get("nuts_bolts", ""),
            row_dict.get("cleat", ""),
            row_dict.get("gasket", ""),
            row_dict.get("corner_pieces", ""),
            round(row_dict.get("weight", 0), 2),
        ]

        # Accumulate totals
        totals["quantity"] += row_dict.get("quantity", 0) or 0
        totals["area"] += area
        totals["24G"] += g24
        totals["22G"] += g22
        totals["20G"] += g20
        totals["18G"] += g18
        totals["weight"] += row_dict.get("weight", 0) or 0

        data.append(formatted_row)

    # Final Total Row
    total_row = [""] * len(headers)
    total_row[headers.index("H1")] = "Total"
    for key in totals:
        if key in headers:
            total_row[headers.index(key)] = round(totals[key], 2)
    data.append(total_row)

    # Draw the table
    table = Table(data, repeatRows=1, colWidths=[45] * len(headers))
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))

    table.wrapOn(p, width, height)
    table_height = 12 * len(data)
    table.drawOn(p, 40, height - 130 - table_height)

    # Footer for signatures
    p.setFont("Helvetica", 9)
    p.drawString(40, 40, "Engineer Signature: __________________")
    p.drawString(350, 40, "Client Signature: __________________")

    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name=f"{client_name}_duct_table.pdf",
                     mimetype='application/pdf')
    
 
# ---------- ✅ Export Excel ----------

@app.route("/export_excel/<int:project_id>")
def export_excel(project_id):
    try:
        conn = sqlite3.connect("database.db")
        query = "SELECT * FROM duct_entries WHERE project_id = ?"
        df = pd.read_sql_query(query, conn, params=(project_id,))
        conn.close()

        if df.empty:
            return "No data available for this project.", 404

        file_path = f"project_{project_id}_entries.xlsx"
        df.to_excel(file_path, index=False)

        return send_file(file_path, as_attachment=True)

    except Exception as e:
        return f"Error exporting data: {e}", 500

    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

# ---------- ✅ Production View ----------
@app.route("/production/<int:project_id>")
def production(project_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cur.fetchone()
    if not project:
        flash("Project not found", "danger")
        return redirect(url_for("projects"))

    cur.execute("SELECT * FROM duct_entries WHERE project_id = ?", (project_id,))
    ducts = cur.fetchall()

    total_area = sum(float(d["area"] or 0) for d in ducts)
    total_nuts = sum(float(d["nuts_bolts"] or 0) for d in ducts)
    total_cleat = sum(float(d["cleat"] or 0) for d in ducts)
    total_gasket = sum(float(d["gasket"] or 0) for d in ducts)
    total_corner = sum(float(d["corner_pieces"] or 0) for d in ducts)
    total_weight = sum(float(d["weight"] or 0) for d in ducts)

    cur.execute("UPDATE projects SET total_sqm = ? WHERE id = ?", (total_area, project_id))
    conn.commit()

    cur.execute("SELECT * FROM production_progress WHERE project_id = ?", (project_id,))
    progress = cur.fetchone()

    if not progress:
        cur.execute("""
            INSERT INTO production_progress (
              project_id, sheet_cutting_sqm, plasma_fabrication_sqm, 
              boxing_assembly_sqm, quality_check_pct, dispatch_percent
            ) VALUES (?, 0, 0, 0, 0, 0)
        """, (project_id,))
        conn.commit()
        cur.execute("SELECT * FROM production_progress WHERE project_id = ?", (project_id,))
        progress = cur.fetchone()

    # Calculate stage-wise percentage (based on sqm)
    sheet_pct = ((progress["sheet_cutting_sqm"] or 0) / total_area * 100) if total_area else 0
    plasma_pct = ((progress["plasma_fabrication_sqm"] or 0) / total_area * 100) if total_area else 0
    boxing_pct = ((progress["boxing_assembly_sqm"] or 0) / total_area * 100) if total_area else 0
    qc_pct = float(progress["quality_check_pct"] or 0)
    dispatch_pct = float(progress["dispatch_percent"] or 0)

    stages = [sheet_pct, plasma_pct, boxing_pct, qc_pct, dispatch_pct]
    overall_progress = sum(stages) / 5

    progress_dict = dict(progress)
    progress_dict.update({
        "sheet_cutting_pct": round(sheet_pct, 1),
        "plasma_fabrication_pct": round(plasma_pct, 1),
        "boxing_assembly_pct": round(boxing_pct, 1),
        "quality_check_pct": round(qc_pct, 1),
        "dispatch_pct": round(dispatch_pct, 1),
        "overall_progress": round(overall_progress, 1),
    })

    conn.close()
    return render_template("production.html",
                           project=project,
                           ducts=ducts,
                           progress=progress_dict,
                           total_area=total_area,
                           total_nuts=total_nuts,
                           total_cleat=total_cleat,
                           total_gasket=total_gasket,
                           total_corner=total_corner,
                           total_weight=total_weight)



@app.route("/update_production/<int:project_id>", methods=["POST"])
def update_production(project_id):
    sheet = float(request.form.get("sheet_cutting") or 0)
    plasma = float(request.form.get("plasma_fabrication") or 0)
    boxing = float(request.form.get("boxing_assembly") or 0)
    qc = float(request.form.get("quality_check") or 0)
    dispatch = float(request.form.get("dispatch") or 0)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE production_progress SET
            sheet_cutting_sqm = ?,
            plasma_fabrication_sqm = ?,
            boxing_assembly_sqm = ?,
            quality_check_pct = ?,
            dispatch_percent = ?
        WHERE project_id = ?
    """, (sheet, plasma, boxing, qc, dispatch, project_id))
    conn.commit()
    conn.close()
    return redirect(url_for("production", project_id=project_id))

# ---------- ✅ Production Overview ----------

@app.route("/production_overview")
def production_overview():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects")
    projects = cur.fetchall()
    conn.close()
    return render_template("production_overview.html", projects=projects)

def get_summary_data():
    conn = get_db()  # ✅ FIXED
    cur = conn.cursor()

    cur.execute('SELECT * FROM projects')
    projects = cur.fetchall()

    cur.execute('SELECT * FROM production_progress')
    production = cur.fetchall()

    cur.execute('SELECT * FROM duct_entries')
    ducts = cur.fetchall()

    conn.close()

    return {
        'projects': [dict(row) for row in projects],
        'production': [dict(row) for row in production],
        'ducts': [dict(row) for row in ducts]
    }

# ---------- ✅ Summary Placeholder ----------
@app.route("/summary", methods=["GET", "POST"])
def summary():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id, project_code FROM projects")
    projects = cur.fetchall()

    if request.method == "POST":
        project_id = request.form.get("project_id")
        source_diagram = request.files.get("source_diagram")
        md_sig = request.files.get("md_signature")
        pm_sig = request.files.get("pm_signature")

        # Area per gauge
        gauges = ['24g', '22g', '20g', '18g']
        areas = {g: float(request.form.get(g, 0)) for g in gauges}

        # Stages progress
        stages = {
            'Sheet Cutting': float(request.form.get('sheet_cutting', 0)),
            'Plasma Fabrication': float(request.form.get('plasma_fabrication', 0)),
            'Boxing & Assembly': float(request.form.get('boxing_assembly', 0)),
            'Quality Checking': float(request.form.get('quality_checking', 0)),
            'Dispatch': float(request.form.get('dispatch', 0)),
        }
        overall = round(sum(stages.values()) / len(stages), 2)

        # Load images
        from io import BytesIO
        from PIL import Image
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib import colors

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
        width, height = landscape(A4)

        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(30, height - 40, "Project Summary Report")

        y = height - 80
        pdf.setFont("Helvetica", 12)
        pdf.drawString(30, y, f"Project ID: {project_id}")
        y -= 20

        # Gauge table
        data = [["Gauge", "Area (sq.m)"]] + [[k.upper(), str(v)] for k, v in areas.items()]
        table = Table(data, colWidths=[100, 150])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        table.wrapOn(pdf, width, height)
        table.drawOn(pdf, 30, y - 100)
        y -= 120

        # Stage progress table
        data2 = [["Stage", "Progress (%)"]] + [[k, str(v)] for k, v in stages.items()] + [["Overall", f"{overall} %"]]
        table2 = Table(data2, colWidths=[200, 150])
        table2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        table2.wrapOn(pdf, width, height)
        table2.drawOn(pdf, 300, y - 100)

        # Draw signatures
        def draw_signature(img, x, y, label):
            img = Image.open(BytesIO(img.read())).resize((120, 40))
            img_io = BytesIO()
            img.save(img_io, format="PNG")
            img_io.seek(0)
            pdf.setFont("Helvetica", 10)
            pdf.drawString(x, y + 45, label)
            pdf.drawInlineImage(img_io, x, y, width=120, height=40)

        draw_signature(md_sig, 50, 40, "Managing Director")
        draw_signature(pm_sig, 250, 40, "Project Manager")

        # Optional: embed source diagram if needed
        if source_diagram:
            img = Image.open(BytesIO(source_diagram.read())).resize((150, 100))
            img_io = BytesIO()
            img.save(img_io, format="PNG")
            img_io.seek(0)
            pdf.drawString(600, height - 300, "Source Diagram")
            pdf.drawInlineImage(img_io, 600, height - 420, width=150, height=100)

        pdf.save()
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="summary_report.pdf", mimetype="application/pdf")

    return render_template("summary.html", projects=projects)
# ---------- ✅ Submit Full Project and Move to Production ----------

@app.route('/submit_all/<project_id>', methods=['POST'])
def submit_all(project_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("UPDATE projects SET status = 'submitted' WHERE id = ?", (project_id,))

    # Optionally lock duct entries
    # cur.execute("UPDATE duct_entries SET status = 'locked' WHERE project_id = ?", (project_id,))

    conn.commit()
    conn.close()

    flash("✅ Project submitted and moved to production.", "success")
    return redirect(url_for('production', project_id=project_id))

# ---------- ✅ Delete Project and Related Ducts ----------

@app.route('/project/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM duct_entries WHERE project_id = ?", (project_id,))
    cur.execute("DELETE FROM production_progress WHERE project_id = ?", (project_id,))
    cur.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    conn.commit()
    conn.close()

    flash("🗑️ Project deleted successfully!", "success")
    return redirect(url_for('projects'))



@app.route('/register_employee', methods=['GET', 'POST'])
def register_employee():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            gender = request.form.get('gender', '')
            dob = request.form.get('dob', '')
            blood_group = request.form.get('blood_group', '')
            department = request.form.get('department', '')
            designation = request.form.get('designation', '')
            email = request.form.get('email', '')
            phone = request.form.get('phone', '')
            join_date = request.form.get('join_date', '')
            address = request.form.get('address', '')
            role = request.form.get('role', 'Employee')

            # Handle photo upload
            photo = request.files.get('photo')
            photo_filename = None
            if photo and photo.filename != '':
                photo_folder = os.path.join('static', 'employee_photos')
                os.makedirs(photo_folder, exist_ok=True)
                photo_filename = f"{uuid.uuid4().hex}_{photo.filename}"
                photo.save(os.path.join(photo_folder, photo_filename))

            # Generate employee ID (format: VE/EMP/0001)
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM employees")
            emp_count = cur.fetchone()[0] + 1
            emp_id = f"VE/EMP/{str(emp_count).zfill(4)}"

            # Hash the default password
            default_password = generate_password_hash('emp@123')

            # Insert into database
            cur.execute('''
                INSERT INTO employees (
                    emp_id, name, gender, dob, blood_group,
                    department, designation, email, phone, join_date,
                    address, role, photo_filename, password
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                emp_id, name, gender, dob, blood_group,
                department, designation, email, phone, join_date,
                address, role, photo_filename, default_password
            ))
            conn.commit()
            conn.close()

            flash("✅ Employee registered successfully!", "success")
            return redirect(url_for('employee_list'))

        except Exception as e:
            import traceback
            traceback.print_exc()
            flash(f"❌ Error: {str(e)}", "danger")
            return redirect(url_for('register_employee'))

    return render_template('register_employee.html')
    # --- GET method: show the form ---
    
@app.route('/employee_list')
def employee_list():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    # Get filters from query params
    department = request.args.get('department', '')
    role = request.args.get('role', '')

    query = "SELECT * FROM employees WHERE 1=1"
    params = []

    if department:
        query += " AND department = ?"
        params.append(department)
    if role:
        query += " AND role = ?"
        params.append(role)

    cur.execute(query, params)
    employees = cur.fetchall()

    # Get unique department and role values for filters
    cur.execute("SELECT DISTINCT department FROM employees")
    departments = [row['department'] for row in cur.fetchall()]
    cur.execute("SELECT DISTINCT role FROM employees")
    roles = [row['role'] for row in cur.fetchall()]

    conn.close()
    return render_template("employee_list.html", employees=employees, departments=departments, roles=roles, selected_department=department, selected_role=role)
@app.route('/delete_employee/<path:emp_id>', methods=['POST'])
def delete_employee(emp_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM employees WHERE emp_id = ?", (emp_id,))
    cur.execute("DELETE FROM users WHERE email = ?", (emp_id,))
    conn.commit()
    conn.close()

    flash("🗑️ Employee deleted successfully.", "success")
    return redirect(url_for('employee_list'))

@app.route('/edit_employee/<path:emp_id>', methods=['GET', 'POST'])
def edit_employee(emp_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        department = request.form['department']
        designation = request.form['designation']
        phone = request.form['phone']
        email = request.form['email']
        role = request.form['role']
        address = request.form['address']

        cur.execute('''
            UPDATE employees SET name=?, department=?, designation=?, phone=?, email=?, role=?, address=?
            WHERE emp_id=?
        ''', (name, department, designation, phone, email, role, address, emp_id))
        conn.commit()
        conn.close()

        flash("✅ Employee details updated.", "success")
        return redirect(url_for('employee_list'))

    else:
        cur.execute("SELECT * FROM employees WHERE emp_id=?", (emp_id,))
        employee = cur.fetchone()
        conn.close()
        if employee:
            return render_template('edit_employee.html', employee=employee)
        else:
            flash("⚠️ Employee not found.", "danger")
            return redirect(url_for('employee_list'))
@app.route('/export_employees')
def export_employees():
    import pandas as pd
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM employees", conn)
    conn.close()

    output_file = f"/tmp/employee_list.xlsx"
    df.to_excel(output_file, index=False)
    return send_file(output_file, as_attachment=True)
@app.route('/download_id_card/<path:emp_id>')
def download_id_card(emp_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM employees WHERE emp_id = ?", (emp_id,))
        emp = cur.fetchone()
        conn.close()

        if not emp:
            return "Employee not found", 404

        from reportlab.pdfgen import canvas
        safe_emp_id = emp_id.replace("/", "_")  # <-- important fix
        pdf_path = f"/tmp/{safe_emp_id}_id_card.pdf"
        c = canvas.Canvas(pdf_path, pagesize=(300, 200))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, 180, "VANES ENGINEERING")
        c.setFont("Helvetica", 10)
        c.drawString(20, 150, f"Emp ID: {emp['emp_id']}")
        c.drawString(20, 135, f"Name: {emp['name']}")
        c.drawString(20, 120, f"Dept: {emp['department']}")
        c.drawString(20, 105, f"Role: {emp['role']}")
        c.drawString(20, 90, f"Join Date: {emp['join_date']}")
        c.drawString(20, 60, "Signature: _______________")
        c.showPage()
        c.save()

        return send_file(pdf_path, as_attachment=True, download_name=f"{emp_id}_ID_Card.pdf")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return "Internal Error in ID card route", 500

@app.route('/download_joining_letter/<path:emp_id>')
def download_joining_letter(emp_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM employees WHERE emp_id = ?", (emp_id,))
        emp = cur.fetchone()
        conn.close()

        if not emp:
            return "Employee not found", 404

        from reportlab.pdfgen import canvas
        safe_emp_id = emp_id.replace("/", "_")  # <-- important fix
        pdf_path = f"/tmp/{safe_emp_id}_joining_letter.pdf"
        c = canvas.Canvas(pdf_path)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 800, "Joining Letter")
        c.setFont("Helvetica", 11)
        c.drawString(40, 770, f"Date: {emp['join_date']}")
        c.drawString(40, 740, f"To: {emp['name']},")
        c.drawString(40, 720, f"Department: {emp['department']}")
        c.drawString(40, 700, f"Designation: {emp['designation']}")
        c.drawString(40, 660, f"Dear {emp['name']},")
        c.drawString(40, 640, "We are pleased to confirm your joining as a valued team member.")
        c.drawString(40, 620, "You are appointed as:")
        c.drawString(60, 600, f"Role: {emp['role']}")
        c.drawString(40, 560, "Please contact HR for further onboarding.")
        c.drawString(40, 520, "Regards,")
        c.drawString(40, 500, "Vanes Engineering")
        c.showPage()
        c.save()

        return send_file(pdf_path, as_attachment=True, download_name=f"{emp_id}_Joining_Letter.pdf")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return "Internal Error in joining letter route", 500

@app.route('/reset_password/<string:username>', methods=['POST'])
def reset_password(username):
    if 'user' not in session:
        return redirect(url_for('login'))

    import hashlib
    new_password = "emp@123"
    hashed = hashlib.sha256(new_password.encode()).hexdigest()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password = ? WHERE username = ?", (hashed, username))
    conn.commit()
    conn.close()

    flash("🔐 Password reset to 'emp@123'.", "info")
    return redirect(url_for('employee_list'))


@app.route('/attendance')
def attendance_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees")
    employees = cur.fetchall()
    conn.close()

    return render_template('attendance.html', employees=employees)


from datetime import datetime

@app.route('/mark_attendance', methods=['GET', 'POST'])
def mark_attendance():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        for emp_id in request.form.getlist('emp_id'):
            status = request.form.get(f'status_{emp_id}', 'Absent')
            check_in = request.form.get(f'check_in_{emp_id}', '')
            check_out = request.form.get(f'check_out_{emp_id}', '')
            date_today = datetime.today().strftime('%Y-%m-%d')

            cur.execute('''
                INSERT INTO attendance (emp_id, date, status, check_in, check_out)
                VALUES (?, ?, ?, ?, ?)
            ''', (emp_id, date_today, status, check_in, check_out))
        
        conn.commit()
        conn.close()
        flash("✅ Attendance marked successfully!", "success")
        return redirect(url_for('attendance_dashboard'))  # redirect to main dashboard

    # GET method
    cur.execute("SELECT emp_id, name FROM employees ORDER BY emp_id")
    employees = cur.fetchall()
    conn.close()
    return render_template("attendance.html", employees=employees)

@app.route('/attendance_list', methods=['GET'])
def attendance_list():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    # Filter by date
    date_filter = request.args.get('date', '')
    if date_filter:
        cur.execute('''
            SELECT a.*, e.name FROM attendance a
            JOIN employees e ON a.emp_id = e.emp_id
            WHERE date = ?
            ORDER BY a.date DESC
        ''', (date_filter,))
    else:
        cur.execute('''
            SELECT a.*, e.name FROM attendance a
            JOIN employees e ON a.emp_id = e.emp_id
            ORDER BY a.date DESC LIMIT 50
        ''')

    records = cur.fetchall()
    conn.close()
    return render_template("attendance_list.html", records=records, selected_date=date_filter)



@app.route('/export_attendance_excel')
def export_attendance_excel():
    import pandas as pd

    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        SELECT a.emp_id, e.name, a.date, a.status, a.check_in, a.check_out
        FROM attendance a
        JOIN employees e ON a.emp_id = e.emp_id
        ORDER BY a.date DESC
    ''')
    data = cur.fetchall()
    conn.close()

    df = pd.DataFrame(data, columns=["Employee ID", "Name", "Date", "Status", "Check-In", "Check-Out"])
    path = "/tmp/attendance_report.xlsx"
    df.to_excel(path, index=False)

    return send_file(path, as_attachment=True, download_name="Attendance_Report.xlsx")



# 🔽 Add the download route after other routes
@app.route('/debug_data')
def debug_data():
    from markupsafe import Markup
    conn = get_db()
    cur = conn.cursor()

    tables = ["projects", "vendors", "duct_entries", "employees", "attendance"]
    html = "<h2>📊 Stored Data in All Tables</h2>"

    for table in tables:
        html += f"<h3>Table: {table}</h3><table border='1' cellpadding='5'><tr>"

        try:
            cur.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()

            if not rows:
                html += "</tr><tr><td colspan='99'>No data</td></tr></table>"
                continue

            # Table headers
            for col in rows[0].keys():
                html += f"<th>{col}</th>"
            html += "</tr>"

            # Table rows
            for row in rows:
                html += "<tr>"
                for val in row:
                    html += f"<td>{val}</td>"
                html += "</tr>"
            html += "</table>"

        except Exception as e:
            html += f"<tr><td colspan='99'>❌ Error reading table '{table}': {e}</td></tr></table>"

    conn.close()
    return Markup(html)



# ---------- ✅ Run Flask App ----------

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
