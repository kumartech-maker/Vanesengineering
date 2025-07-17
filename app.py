from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from datetime import datetime
import sqlite3
import os
import pandas as pd
import math
from num2words import num2words
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'secretkey'

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Attendance table
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

    # Employees table
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

    # Employee login
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

    # Projects table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_code TEXT,
            vendor_id INTEGER,
            quotation_ro TEXT,
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            incharge TEXT,
            notes TEXT,
            file_name TEXT,
            enquiry_id TEXT,
            client_name TEXT,
            site_location TEXT,
            engineer_name TEXT,
            mobile TEXT,
            status TEXT DEFAULT 'new',
            total_sqm REAL DEFAULT 0,
            FOREIGN KEY(vendor_id) REFERENCES vendors(id)
        )
    ''')

    # Duct entries table
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

    # Vendors
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

    # Users
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

    # Recreate production_progress
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

    # Dummy employees
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

    # Dummy attendance
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

    # Default admin
    cur.execute('''
        INSERT OR IGNORE INTO users (email, name, role, contact, password)
        VALUES (?, ?, ?, ?, ?)
    ''', ("admin@ducting.com", "Admin", "Admin", "9999999999", "admin123"))

    # Default vendor
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

# Auto-init DB on every request
@app.before_request
def setup_db_on_request():
    init_db()
# ---------- ✅ Login ----------

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cur.fetchone()

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
    cur.execute("SELECT * FROM projects ORDER BY id DESC")
    projects = cur.fetchall()
    cur.execute("SELECT * FROM vendors ORDER BY id DESC")
    vendors = cur.fetchall()
    conn.close()

    project = projects[0] if projects else None

    return render_template('projects.html',
                           projects=projects,
                           vendors=vendors,
                           project=project,
                           enquiry_id="ENQ" + str(datetime.now().timestamp()).replace(".", ""))

# ---------- ✅ Create Project ----------
@app.route('/create_project', methods=['POST'])
def create_project():
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        vendor_id = request.form['vendor_id']
        project_name = request.form['project_name']
        enquiry_no = request.form['enquiry_no']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        incharge = request.form['incharge']
        notes = request.form['notes']
        file = request.files.get('drawing_file')
        file_name = None

        if file and file.filename != '':
            uploads_dir = os.path.join('static', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            file_name = file.filename
            file.save(os.path.join(uploads_dir, file_name))

        # ✅ Connect to DB
        conn = get_db()
        cur = conn.cursor()

        # ✅ Insert project without project_code
        cur.execute('''
            INSERT INTO projects (
                vendor_id, quotation_ro, start_date, end_date,
                location, incharge, notes, file_name,
                enquiry_id, client_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            vendor_id, '', start_date, end_date,
            '', incharge, notes, file_name,
            enquiry_no, project_name
        ))

        project_id = cur.lastrowid

        # ✅ Generate custom project code: VE/2526/E001
        custom_year = 2526  # Change this if you want dynamic logic
        project_code = f"VE/{custom_year}/E{str(project_id).zfill(3)}"

        cur.execute("UPDATE projects SET project_code = ? WHERE id = ?", (project_code, project_id))

        conn.commit()
        conn.close()

        flash("✅ Project added successfully!", "success")
        return redirect(url_for('projects'))

    except Exception as e:
        import traceback
        traceback.print_exc()
        return "❌ Failed to create project", 400

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
    cur.execute('''
        UPDATE projects SET
        client_name = ?, site_location = ?, engineer_name = ?, mobile = ?, status = ?
        WHERE id = ?
    ''', (client_name, site_location, engineer_name, mobile, 'preparation', project_id))
    conn.commit()
    conn.close()
    return '', 200

# ---------- ✅ Open Specific Project and Duct Entries ----------

@app.route('/project/<int:project_id>')
def open_project(project_id):
    conn = get_db()
    cur = conn.cursor()

    # Fetch project info
    cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cur.fetchone()
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('projects'))

    # Fetch vendors
    cur.execute("SELECT * FROM vendors")
    vendors = cur.fetchall()

    # Fetch duct entries
    cur.execute("SELECT * FROM duct_entries WHERE project_id = ?", (project_id,))
    duct_rows = cur.fetchall()

    # Initialize
    ducts = []
    total_area = total_nuts = total_cleat = total_gasket = total_corner = total_weight = 0.0
    gauge_area_totals = {"24G": 0.0, "22G": 0.0, "20G": 0.0, "18G": 0.0}

    # Process each duct row
    for row in duct_rows:
        d = dict(row)

        # Parse fields safely
        area = float(d.get('area') or 0)
        nuts = float(d.get('nuts_bolts') or 0)
        cleat = float(d.get('cleat') or 0)
        gasket = float(d.get('gasket') or 0)
        corner = float(d.get('corner_pieces') or 0)
        weight = float(d.get('weight') or 0)
        gauge = d.get('gauge', '').strip()

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

        # Add back to dict
        d['area'] = area
        d['nuts_bolts'] = nuts
        d['cleat'] = cleat
        d['gasket'] = gasket
        d['corner_pieces'] = corner
        d['weight'] = weight

        ducts.append(d)

    conn.close()

    return render_template("projects.html",
                           project=project,
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
def edit_duct(entry_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM duct_entries WHERE id = ?", (entry_id,))
    entry = cur.fetchone()
    if not entry:
        flash("Entry not found", "danger")
        return redirect(url_for("projects"))

    project_id = entry["project_id"]

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

    # Fetch data to re-render form in edit mode
    cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cur.fetchone()
    cur.execute("SELECT * FROM vendors")
    vendors = cur.fetchall()
    cur.execute("SELECT * FROM duct_entries WHERE project_id = ?", (project_id,))
    entries = cur.fetchall()

    def safe_float(val): return float(val) if val else 0
    total_area = sum(safe_float(d['area']) for d in entries)
    total_nuts = sum(safe_float(d['nuts_bolts']) for d in entries)
    total_cleat = sum(safe_float(d['cleat']) for d in entries)
    total_gasket = sum(safe_float(d['gasket']) for d in entries)
    total_corner = sum(safe_float(d['corner_pieces']) for d in entries)

    conn.close()
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
    from num2words import num2words
    import os
    import sqlite3

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Project Info
    c.execute("SELECT client_name, site_location, engineer_name, mobile, start_date, end_date FROM projects WHERE id = ?", (project_id,))
    proj = c.fetchone()
    client_name, site_location, engineer_name, mobile, start_date, end_date = proj or ("", "", "", "", "", "")

    # Header
    logo_path = os.path.join("static", "logo.png")
    if os.path.exists(logo_path):
        p.drawImage(logo_path, 40, height - 80, width=80, preserveAspectRatio=True, mask='auto')

    p.setFont("Helvetica-Bold", 16)
    p.drawString(150, height - 50, "Vanes Engineering Pvt Ltd")
    p.setFont("Helvetica", 10)
    p.drawString(150, height - 65, "No. 23, Industrial Estate, Chennai")
    p.drawString(150, height - 78, "Email: info@vanesengineering.com | Phone: +91-98765-43210")

    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, height - 110, f"Client: {client_name}")
    p.drawString(350, height - 110, f"Site: {site_location}")
    p.drawString(40, height - 125, f"Engineer: {engineer_name}")
    p.drawString(350, height - 125, f"Mobile: {mobile}")
    p.drawString(40, height - 140, f"Duration: {start_date} to {end_date}")

    # Duct Entries with gauge area handling
    c.execute('''
        SELECT duct_no, duct_type, width1, height1, length_or_radius, quantity, degree_or_offset, factor, gauge,
               area, nuts_bolts, cleat, gasket, corner_pieces, weight
        FROM duct_entries
        WHERE project_id = ?
    ''', (project_id,))
    rows = c.fetchall()
    conn.close()

    headers = ["Duct No", "Type", "W", "H", "L/R", "Qty", "Deg", "Factor", "Gauge",
               "Area", "24G", "22G", "20G", "18G", "Nuts", "Cleat", "Gasket", "Corner", "Weight"]
    data = [headers]
    totals = [0] * len(headers)

    for r in rows:
        duct_no, duct_type, w, h, l, qty, deg, factor, gauge, area, nuts, cleat, gasket, corner, weight = r

        # Determine gauge area
        area_24 = area_22 = area_20 = area_18 = 0
        if gauge.strip() == "24G":
            area_24 = area
        elif gauge.strip() == "22G":
            area_22 = area
        elif gauge.strip() == "20G":
            area_20 = area
        elif gauge.strip() == "18G":
            area_18 = area

        row_data = [
            duct_no, duct_type, w, h, l, qty, deg, factor, gauge,
            round(area, 2), round(area_24, 2), round(area_22, 2), round(area_20, 2), round(area_18, 2),
            nuts, cleat, gasket, corner, weight
        ]

        for i in range(len(row_data)):
            try:
                if isinstance(row_data[i], (int, float)):
                    totals[i] += float(row_data[i])
            except:
                pass

        data.append(row_data)

    # Total Row
    total_row = [""] * len(headers)
    total_row[1] = "TOTAL"
    for i in range(len(totals)):
        if isinstance(totals[i], float) or isinstance(totals[i], int):
            total_row[i] = round(totals[i], 2)
    data.append(total_row)

    # Draw table
    table = Table(data, repeatRows=1, colWidths=[45] * len(headers))
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    table.wrapOn(p, width, height)
    table_height = 12 * len(data)
    table.drawOn(p, 40, height - 160 - table_height)

    def to_words(val):
        try:
            return f"{num2words(int(val)).capitalize()} point {num2words(int(round((val - int(val)) * 100)))}"
        except:
            return "Not available"

    p.setFont("Helvetica-Bold", 8)
    p.drawString(40, 80, f"Total Area in Words: {to_words(totals[9])} sq.m")
    p.drawString(350, 80, f"Total Weight in Words: {to_words(totals[19])} kg")

    p.setFont("Helvetica", 9)
    p.drawString(40, 60, "Engineer Signature: __________________")
    p.drawString(350, 60, "Client Signature: __________________")

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

# ---------- ✅ Summary Placeholder ----------

@app.route('/summary')
def summary():
    return "<h2>Summary Coming Soon...</h2>"

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




# ---------- ✅ Run Flask App ----------

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
