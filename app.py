from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from datetime import datetime
from io import BytesIO
import sqlite3
import os
import pandas as pd
import math
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from num2words import num2words

app = Flask(__name__)
app.secret_key = 'secretkey'

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_code TEXT UNIQUE,
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
        CREATE TABLE IF NOT EXISTS production_progress (  
            id INTEGER PRIMARY KEY AUTOINCREMENT,  
            project_id INTEGER,  
            sheet_cutting_sqm REAL DEFAULT 0,  
            plasma_fabrication_sqm REAL DEFAULT 0,  
            boxing_assembly_sqm REAL DEFAULT 0  
        )  
    ''')

    # Default Admin
    cur.execute('''  
        INSERT OR IGNORE INTO users (email, name, role, contact, password)  
        VALUES (?, ?, ?, ?, ?)  
    ''', ("admin@ducting.com", "Admin", "Admin", "9999999999", "admin123"))

    # Default Vendor
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

        # Generate formatted project_code like VE/TN/2526/P001
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM projects")
        count = cur.fetchone()[0] + 1
        year_code = datetime.now().strftime('%y') + str(int(datetime.now().strftime('%y')) + 1)
        project_code = f"VE/TN/{year_code}/P{str(count).zfill(3)}"

        cur.execute('''
            INSERT INTO projects (
                project_code, vendor_id, quotation_ro, start_date, end_date,
                location, incharge, notes, file_name,
                enquiry_id, client_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_code, vendor_id, '', start_date, end_date,
            '', incharge, notes, file_name,
            enquiry_no, project_name
        ))

        conn.commit()
        conn.close()
        flash("✅ Project added successfully!", "success")
        return redirect(url_for('projects'))

    except Exception as e:
        print("❌ Error while creating project:", e)
        return "Bad Request", 400


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

    # Convert and compute
    ducts = []
    for row in duct_rows:
        d = dict(row)
        d['area'] = float(d.get('area') or 0)
        d['nuts_bolts'] = float(d.get('nuts_bolts') or 0)
        d['cleat'] = float(d.get('cleat') or 0)
        d['gasket'] = float(d.get('gasket') or 0)
        d['corner_pieces'] = float(d.get('corner_pieces') or 0)
        d['weight'] = float(d.get('weight') or 0)
        ducts.append(d)

    total_area = sum(d['area'] for d in ducts)
    total_nuts = sum(d['nuts_bolts'] for d in ducts)
    total_cleat = sum(d['cleat'] for d in ducts)
    total_gasket = sum(d['gasket'] for d in ducts)
    total_corner = sum(d['corner_pieces'] for d in ducts)

    conn.close()
    return render_template("projects.html",
                           project=project,
                           vendors=vendors,
                           ducts=ducts,
                           total_area=total_area,
                           total_nuts=total_nuts,
                           total_cleat=total_cleat,
                           total_gasket=total_gasket,
                           total_corner=total_corner)


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

    # Calculate area
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

    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO duct_entries (
            project_id, duct_no, duct_type, width1, height1, width2, height2,
            quantity, length_or_radius, degree_or_offset, factor,
            area, gauge, nuts_bolts, cleat, gasket, corner_pieces
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        project_id, duct_no, duct_type, w1, h1, w2, h2,
        qty, length, deg, factor,
        round(area, 2), gauge, round(nuts_bolts, 2), round(cleat, 2),
        round(gasket, 2), round(corner_pieces, 2)
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
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    from io import BytesIO
    from num2words import num2words
    import os

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT client_name, site_location, engineer_name, mobile, start_date, end_date FROM projects WHERE id = ?", (project_id,))
    proj = c.fetchone()
    conn.close()

    client_name = proj[0] if proj else "Project"
    site_location = proj[1] if proj else ""
    engineer_name = proj[2] if proj else ""
    mobile = proj[3] if proj else ""
    start_date = proj[4] if proj else ""
    end_date = proj[5] if proj else ""

    # Header
    logo_path = os.path.join("static", "logo.png")
    if os.path.exists(logo_path):
        p.drawImage(logo_path, 50, height - 80, width=80, preserveAspectRatio=True, mask='auto')

    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, height - 50, "Vanes Engineering Pvt Ltd")
    p.setFont("Helvetica", 10)
    p.drawString(200, height - 65, "No. 23, Industrial Estate, Chennai")
    p.drawString(200, height - 78, "Email: info@vanesengineering.com | Phone: +91-98765-43210")

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 110, f"Client: {client_name}")
    p.drawString(300, height - 110, f"Site: {site_location}")
    p.drawString(50, height - 125, f"Engineer: {engineer_name}")
    p.drawString(300, height - 125, f"Mobile: {mobile}")
    p.drawString(50, height - 140, f"Duration: {start_date} to {end_date}")

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT duct_no, duct_type, width1, height1, quantity, area, weight FROM duct_entries WHERE project_id = ?", (project_id,))
    entries = c.fetchall()
    conn.close()

    data = [["Duct No", "Type", "Width", "Height", "Qty", "Area", "Weight"]]
    total_qty = total_area = total_weight = 0
    for row in entries:
        w = float(row[2] or 0)
        h = float(row[3] or 0)
        qty = float(row[4] or 0)
        area = float(row[5] or 0)
        weight = float(row[6] or 0)
        data.append([row[0], row[1], w, h, qty, area, weight])
        total_qty += qty
        total_area += area
        total_weight += weight
    data.append(["", "", "", "Total", total_qty, round(total_area, 2), round(total_weight, 2)])

    table = Table(data, colWidths=[60, 55, 50, 50, 50, 60, 60])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER')
    ]))
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 190 - 25 * len(data))

    def convert_to_words(value):
        try:
            int_part = int(value)
            decimal_part = int(round((value - int_part) * 100))
            return f"{num2words(int_part).capitalize()} point {num2words(decimal_part)}"
        except:
            return "Not available"

    area_words = convert_to_words(round(total_area, 2))
    weight_words = convert_to_words(round(total_weight, 2))

    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, height - 210 - 25 * len(data), f"Total Area in Words: {area_words} sq.m")
    p.drawString(50, height - 225 - 25 * len(data), f"Total Weight in Words: {weight_words} kg")

    p.setFont("Helvetica", 10)
    p.drawString(50, 80, "Engineer Signature: __________________")
    p.drawString(300, 80, "Client Signature: __________________")

    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name=f"{client_name}_duct_sheet.pdf",
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
        return redirect(url_for('projects'))

    cur.execute("SELECT * FROM duct_entries WHERE project_id = ?", (project_id,))
    ducts = cur.fetchall()

    total_area = 0
    total_nuts = 0
    total_cleat = 0
    total_gasket = 0
    total_corner = 0
    total_weight = 0

    for duct in ducts:
        try:
            area = float(duct["area"] or 0)
            nuts = float(duct["nuts_bolts"] or 0)
            cleat = float(duct["cleat"] or 0)
            gasket = float(duct["gasket"] or 0)
            corner = float(duct["corner_pieces"] or 0)
            weight = float(duct["weight"] or 0)

            total_area += area
            total_nuts += nuts
            total_cleat += cleat
            total_gasket += gasket
            total_corner += corner
            total_weight += weight
        except Exception as e:
            print("❌ Error calculating totals:", e)

    # Update total_sqm in projects table
    cur.execute("UPDATE projects SET total_sqm = ? WHERE id = ?", (total_area, project_id))
    conn.commit()

    # Handle progress tracking
    cur.execute("SELECT * FROM production_progress WHERE project_id = ?", (project_id,))
    progress = cur.fetchone()
    if not progress:
        cur.execute("""
            INSERT INTO production_progress (project_id, sheet_cutting_sqm, plasma_fabrication_sqm, boxing_assembly_sqm)
            VALUES (?, 0, 0, 0)
        """, (project_id,))
        conn.commit()
        cur.execute("SELECT * FROM production_progress WHERE project_id = ?", (project_id,))
        progress = cur.fetchone()

    conn.close()

    return render_template("production.html",
                           project=project,
                           ducts=ducts,
                           progress=progress,
                           total_area=total_area,
                           total_nuts=total_nuts,
                           total_cleat=total_cleat,
                           total_gasket=total_gasket,
                           total_corner=total_corner,
                           total_weight=total_weight)

# ---------- ✅ Update Production Progress ----------

@app.route("/update_production/<int:project_id>", methods=["POST"])
def update_production(project_id):
    sheet_cutting = float(request.form.get("sheet_cutting") or 0)
    plasma_fabrication = float(request.form.get("plasma_fabrication") or 0)
    boxing_assembly = float(request.form.get("boxing_assembly") or 0)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE production_progress
        SET sheet_cutting_sqm = ?, plasma_fabrication_sqm = ?, boxing_assembly_sqm = ?
        WHERE project_id = ?
    """, (sheet_cutting, plasma_fabrication, boxing_assembly, project_id))
    conn.commit()
    conn.close()

    return redirect(url_for('production', project_id=project_id))

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


# ---------- ✅ Run Flask App ----------

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
