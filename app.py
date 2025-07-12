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

    # Default admin user
    cur.execute('''
        INSERT OR IGNORE INTO users (email, name, role, contact, password)
        VALUES (?, ?, ?, ?, ?)
    ''', ("admin@ducting.com", "Admin", "Admin", "9999999999", "admin123"))

    # Dummy vendor and contact
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
def setup_database():
    init_db()
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cur.fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM projects")
    total_projects = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM vendors")
    total_vendors = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    conn.close()

    return render_template("dashboard.html", total_projects=total_projects,
                           total_vendors=total_vendors, total_users=total_users)

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


@app.route('/api/vendor/<int:vendor_id>')
def get_vendor_info(vendor_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT gst, address FROM vendors WHERE id = ?", (vendor_id,))
    vendor = cur.fetchone()
    conn.close()
    if vendor:
        return {'gst': vendor['gst'], 'address': vendor['address']}
    else:
        return {}, 404


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


@app.route('/create_project', methods=['POST'])
def create_project():
    client_name = request.form['client_name']
    site_location = request.form['site_location']
    engineer_name = request.form['engineer_name']
    mobile = request.form['mobile']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    vendor_id = request.form['vendor_id']

    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO projects (client_name, site_location, engineer_name, mobile, start_date, end_date, vendor_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (client_name, site_location, engineer_name, mobile, start_date, end_date, vendor_id))
    conn.commit()
    conn.close()

    flash("✅ Project created successfully!", "success")
    return redirect(url_for('projects'))


@app.route('/project/<int:project_id>')
def open_project(project_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cur.fetchone()

    cur.execute("SELECT * FROM vendors")
    vendors = cur.fetchall()

    cur.execute("SELECT * FROM duct_entries WHERE project_id = ?", (project_id,))
    entries = cur.fetchall()

    # Totals by gauge
    totals_by_gauge = {
        '24g': {'area': 0, 'qty': 0},
        '22g': {'area': 0, 'qty': 0},
        '20g': {'area': 0, 'qty': 0},
        '18g': {'area': 0, 'qty': 0},
    }

    # Overall totals
    total_area = total_nuts = total_cleat = total_gasket = total_corner = 0

    for d in entries:
        gauge = d['gauge']
        area = float(d['area'] or 0)
        qty = int(d['quantity'] or 0)

        if gauge in totals_by_gauge:
            totals_by_gauge[gauge]['area'] += area
            totals_by_gauge[gauge]['qty'] += qty

        total_area += area
        total_nuts += float(d['nuts_bolts'] or 0)
        total_cleat += float(d['cleat'] or 0)
        total_gasket += float(d['gasket'] or 0)
        total_corner += float(d['corner_pieces'] or 0)

    conn.close()
    return render_template("projects.html",
                           project=project,
                           vendors=vendors,
                           entries=entries,
                           total_area=round(total_area, 2),
                           total_nuts=round(total_nuts, 2),
                           total_cleat=round(total_cleat, 2),
                           total_gasket=round(total_gasket, 2),
                           total_corner=round(total_corner, 2),
                           totals_by_gauge=totals_by_gauge)


@app.route('/add_duct/<int:project_id>', methods=['POST'])
def add_duct(project_id):
    import math

    form = request.form
    duct_type = form['duct_type'].upper()
    w1 = float(form.get('width1') or 0)
    h1 = float(form.get('height1') or 0)
    w2 = float(form.get('width2') or 0)
    h2 = float(form.get('height2') or 0)
    qty = int(form.get('quantity') or 0)
    length = float(form.get('length_or_radius') or 0)
    deg = float(form.get('degree_or_offset') or 0)
    factor = float(form.get('factor') or 1)

    # Generate ID: VE/TN/2526/EXXX
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM duct_entries WHERE project_id = ?", (project_id,))
    count = cur.fetchone()[0] + 1
    duct_no = f"VE/TN/2526/E{count:03d}"

    # Area calculation
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

    # Gauge logic
    gauge = '18g'
    if w1 <= 751 and h1 <= 751:
        gauge = '24g'
    elif w1 <= 1201 and h1 <= 1201:
        gauge = '22g'
    elif w1 <= 1800 and h1 <= 1800:
        gauge = '20g'

    nuts_bolts = qty * 4
    cleat_factor = 12
    if gauge == '24g': cleat_factor = 4
    elif gauge == '22g': cleat_factor = 8
    elif gauge == '20g': cleat_factor = 10
    cleat = qty * cleat_factor
    gasket = (w1 + h1 + w2 + h2) / 1000 * qty
    corner_pieces = 0 if duct_type == 'DUM' else qty * 8

    cur.execute('''
        INSERT INTO duct_entries (
            project_id, duct_no, duct_type, width1, height1, width2, height2,
            length_or_radius, degree_or_offset, quantity, gauge, factor, area,
            nuts_bolts, cleat, gasket, corner_pieces
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        project_id, duct_no, duct_type, w1, h1, w2, h2,
        length, deg, qty, gauge, factor, round(area, 2),
        round(nuts_bolts, 2), round(cleat, 2), round(gasket, 2), round(corner_pieces, 2)
    ))

    conn.commit()
    conn.close()
    flash("✅ Duct entry added!", "success")
    return redirect(url_for('open_project', project_id=project_id))


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

    total_area = total_nuts = total_cleat = total_gasket = total_corner = total_weight = 0
    total_24g = total_22g = total_20g = total_18g = 0

    for duct in ducts:
        area = float(duct["area"] or 0)
        nuts = float(duct["nuts_bolts"] or 0)
        cleat = float(duct["cleat"] or 0)
        gasket = float(duct["gasket"] or 0)
        corner = float(duct["corner_pieces"] or 0)
        weight = float(duct["weight"] or 0)
        gauge = duct["gauge"]

        total_area += area
        total_nuts += nuts
        total_cleat += cleat
        total_gasket += gasket
        total_corner += corner
        total_weight += weight

        if gauge == '24g':
            total_24g += area
        elif gauge == '22g':
            total_22g += area
        elif gauge == '20g':
            total_20g += area
        elif gauge == '18g':
            total_18g += area

    cur.execute("UPDATE projects SET total_sqm = ? WHERE id = ?", (total_area, project_id))
    conn.commit()

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
        total_area=round(total_area, 2),
        total_nuts=round(total_nuts, 2),
        total_cleat=round(total_cleat, 2),
        total_gasket=round(total_gasket, 2),
        total_corner=round(total_corner, 2),
        total_weight=round(total_weight, 2),
        total_24g=round(total_24g, 2),
        total_22g=round(total_22g, 2),
        total_20g=round(total_20g, 2),
        total_18g=round(total_18g, 2)
                          )

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


@app.route("/production_overview")
def production_overview():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects")
    projects = cur.fetchall()
    conn.close()
    return render_template("production_overview.html", projects=projects)


@app.route('/summary')
def summary():
    return "<h2>Summary Coming Soon...</h2>"


@app.route('/submit_all/<project_id>', methods=['POST'])
def submit_all(project_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("UPDATE projects SET status = 'submitted' WHERE id = ?", (project_id,))

    # Optional lock logic:
    # cur.execute("UPDATE duct_entries SET status = 'locked' WHERE project_id = ?", (project_id,))

    conn.commit()
    conn.close()

    flash("✅ Project submitted and moved to production.", "success")
    return redirect(url_for('production', project_id=project_id))


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

# ---------- ✅ Run App ----------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))



