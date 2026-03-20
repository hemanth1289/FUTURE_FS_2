"""
Mini CRM - Client Lead Management System
A simple Flask + SQLite application for managing sales leads.
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

# Load environment variables from .env file (if it exists)
load_dotenv()

# ─── App Configuration ────────────────────────────────────────────────────────

app = Flask(__name__)

# Secret key for sessions and flash messages — set in .env or falls back to default
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

# SQLite database stored in the project folder
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///leads.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Admin credentials from environment (defaults for dev)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# How many leads to show per page
LEADS_PER_PAGE = 10

db = SQLAlchemy(app)

# ─── Database Model ───────────────────────────────────────────────────────────

class Lead(db.Model):
    """Represents a single sales lead."""

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(150), nullable=False)
    phone      = db.Column(db.String(20),  nullable=True)
    source     = db.Column(db.String(50),  nullable=True)   # e.g. Website, Referral
    message    = db.Column(db.Text,        nullable=True)
    status     = db.Column(db.String(20),  nullable=False, default='new')
    created_at = db.Column(db.DateTime,    nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Lead {self.name} ({self.status})>'


# ─── Auth Helper ──────────────────────────────────────────────────────────────

def login_required(f):
    """Decorator: redirect to login page if user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access the dashboard.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def index():
    """Public lead submission form."""
    if request.method == 'POST':
        # Grab form data
        name    = request.form.get('name',    '').strip()
        email   = request.form.get('email',   '').strip()
        phone   = request.form.get('phone',   '').strip()
        source  = request.form.get('source',  '').strip()
        message = request.form.get('message', '').strip()

        # ── Validation ──────────────────────────────────────────────────────
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
            # Re-render form with the values the user already typed
            return render_template('index.html',
                                   name=name, email=email,
                                   phone=phone, source=source, message=message)

        # ── Save to database ─────────────────────────────────────────────────
        lead = Lead(name=name, email=email, phone=phone,
                    source=source, message=message)
        db.session.add(lead)
        db.session.commit()

        flash('Thank you! Your message has been received. We\'ll be in touch soon.', 'success')
        return redirect(url_for('index'))

    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page."""
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
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Clear the session and redirect to login."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """
    Main admin dashboard.
    Supports: search, filter by status, pagination, analytics.
    """
    # ── Query params ─────────────────────────────────────────────────────────
    search  = request.args.get('search',  '').strip()
    status  = request.args.get('status',  '')
    page    = request.args.get('page', 1, type=int)

    # ── Build query ──────────────────────────────────────────────────────────
    query = Lead.query

    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(Lead.name.ilike(like), Lead.email.ilike(like))
        )
    if status:
        query = query.filter_by(status=status)

    # Latest leads first
    query = query.order_by(Lead.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=LEADS_PER_PAGE, error_out=False)
    leads      = pagination.items

    # ── Analytics (always on full dataset, not filtered) ─────────────────────
    total_leads     = Lead.query.count()
    new_leads       = Lead.query.filter_by(status='new').count()
    contacted_leads = Lead.query.filter_by(status='contacted').count()
    converted_leads = Lead.query.filter_by(status='converted').count()

    analytics = {
        'total':     total_leads,
        'new':       new_leads,
        'contacted': contacted_leads,
        'converted': converted_leads,
        'conversion_rate': (
            round(converted_leads / total_leads * 100, 1) if total_leads else 0
        ),
    }

    return render_template(
        'dashboard.html',
        leads=leads,
        pagination=pagination,
        analytics=analytics,
        search=search,
        current_status=status,
    )


@app.route('/lead/<int:lead_id>/update-status', methods=['POST'])
@login_required
def update_status(lead_id):
    """Update the status of a lead (AJAX-friendly POST)."""
    lead = Lead.query.get_or_404(lead_id)
    new_status = request.form.get('status')

    allowed = ['new', 'contacted', 'converted']
    if new_status not in allowed:
        flash('Invalid status value.', 'error')
    else:
        lead.status = new_status
        db.session.commit()
        flash(f'Status updated to "{new_status}" for {lead.name}.', 'success')

    # Return to the same page the user was on
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/lead/<int:lead_id>/delete', methods=['POST'])
@login_required
def delete_lead(lead_id):
    """Permanently delete a lead."""
    lead = Lead.query.get_or_404(lead_id)
    name = lead.name
    db.session.delete(lead)
    db.session.commit()
    flash(f'Lead "{name}" has been deleted.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/export')
@login_required
def export_csv():
    """Export all leads (or filtered) to a CSV file download."""
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')

    query = Lead.query
    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(Lead.name.ilike(like), Lead.email.ilike(like))
        )
    if status:
        query = query.filter_by(status=status)

    leads = query.order_by(Lead.created_at.desc()).all()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Source', 'Status', 'Message', 'Created At'])
    for lead in leads:
        writer.writerow([
            lead.id, lead.name, lead.email, lead.phone or '',
            lead.source or '', lead.status, lead.message or '',
            lead.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    output.seek(0)
    filename = f"leads_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


# ─── Bootstrap & Entry Point ──────────────────────────────────────────────────

with app.app_context():
    db.create_all()   # Create tables if they don't exist yet

if __name__ == '__main__':
    app.run(debug=True)
