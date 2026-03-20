"""
Mini CRM - Client Lead Management System
Flask + SQLite + SQLAlchemy
"""

import os
import csv
import io
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, Response
)
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

# ── App setup ────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

# DATABASE_URL from env (set on Render to an absolute sqlite path).
# Falls back to a file next to app.py for local dev.
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'leads.db')
)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

ADMIN_USERNAME  = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD  = os.environ.get('ADMIN_PASSWORD', 'admin123')
LEADS_PER_PAGE  = 10

db = SQLAlchemy(app)

# ── Model ─────────────────────────────────────────────────────────────────────

class Lead(db.Model):
    id         = db.Column(db.Integer,  primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(150), nullable=False)
    phone      = db.Column(db.String(20),  nullable=True)
    source     = db.Column(db.String(50),  nullable=True)
    message    = db.Column(db.Text,        nullable=True)
    status     = db.Column(db.String(20),  nullable=False, default='new')
    created_at = db.Column(db.DateTime,    nullable=False, default=datetime.utcnow)

# ── Auth helper ───────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access the dashboard.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name    = request.form.get('name',    '').strip()
        email   = request.form.get('email',   '').strip()
        phone   = request.form.get('phone',   '').strip()
        source  = request.form.get('source',  '').strip()
        message = request.form.get('message', '').strip()

        errors = []
        if not name:
            errors.append('Name is required.')
        if not email:
            errors.append('Email is required.')
        elif '@' not in email or '.' not in email.split('@')[-1]:
            errors.append('Please enter a valid email address.')

        if errors:
            for err in errors:
                flash(err, 'error')
            return render_template('index.html',
                                   name=name, email=email,
                                   phone=phone, source=source, message=message)

        lead = Lead(name=name, email=email, phone=phone, source=source, message=message)
        db.session.add(lead)
        db.session.commit()
        flash("Thank you! Your message has been received. We'll be in touch soon.", 'success')
        return redirect(url_for('index'))

    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username']  = username
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')
    page   = request.args.get('page', 1, type=int)

    query = Lead.query
    if search:
        like = f'%{search}%'
        query = query.filter(db.or_(Lead.name.ilike(like), Lead.email.ilike(like)))
    if status:
        query = query.filter_by(status=status)
    query = query.order_by(Lead.created_at.desc())

    pagination = query.paginate(page=page, per_page=LEADS_PER_PAGE, error_out=False)
    leads      = pagination.items

    total     = Lead.query.count()
    converted = Lead.query.filter_by(status='converted').count()
    analytics = {
        'total':           total,
        'new':             Lead.query.filter_by(status='new').count(),
        'contacted':       Lead.query.filter_by(status='contacted').count(),
        'converted':       converted,
        'conversion_rate': round(converted / total * 100, 1) if total else 0,
    }

    return render_template('dashboard.html',
                           leads=leads, pagination=pagination,
                           analytics=analytics, search=search,
                           current_status=status)


@app.route('/lead/<int:lead_id>/update-status', methods=['POST'])
@login_required
def update_status(lead_id):
    lead       = Lead.query.get_or_404(lead_id)
    new_status = request.form.get('status')
    if new_status in ('new', 'contacted', 'converted'):
        lead.status = new_status
        db.session.commit()
        flash(f'Status updated to "{new_status}" for {lead.name}.', 'success')
    else:
        flash('Invalid status.', 'error')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/lead/<int:lead_id>/delete', methods=['POST'])
@login_required
def delete_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    name = lead.name
    db.session.delete(lead)
    db.session.commit()
    flash(f'Lead "{name}" deleted.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/export')
@login_required
def export_csv():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')

    query = Lead.query
    if search:
        like = f'%{search}%'
        query = query.filter(db.or_(Lead.name.ilike(like), Lead.email.ilike(like)))
    if status:
        query = query.filter_by(status=status)
    leads = query.order_by(Lead.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID','Name','Email','Phone','Source','Status','Message','Created At'])
    for l in leads:
        writer.writerow([l.id, l.name, l.email, l.phone or '', l.source or '',
                         l.status, l.message or '',
                         l.created_at.strftime('%Y-%m-%d %H:%M:%S')])
    output.seek(0)
    filename = f"leads_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})


# ── Create tables & run ───────────────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)

