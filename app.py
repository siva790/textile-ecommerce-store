from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
import time
import random
from functools import wraps
from datetime import datetime
import io
from dotenv import load_dotenv
# SendGrid for email sending
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
# Optional ReportLab import for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')
app.config['JSON_AS_ASCII'] = False  # Support Unicode characters in JSON responses

# Ensure all responses use UTF-8 encoding
@app.after_request
def after_request(response):
    response.headers['Content-Type'] = response.headers.get('Content-Type', 'text/html') + '; charset=utf-8'
    return response

# SendGrid configuration for OTP emails
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@textilestore.com')
SENDGRID_FROM_NAME = os.getenv('SENDGRID_FROM_NAME', 'Textile Store')

# File upload configuration
UPLOAD_FOLDER = os.path.join('static', 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Mock Payment System - No external service needed!
MOCK_PAYMENT_ENABLED = True

# OTP System - Mock OTP for security verification
# In production, OTPs would be sent via email/SMS
OTP_STORAGE = {}  # Format: {email: {'otp': '123456', 'timestamp': time.time(), 'verified': False, 'type': 'register'}}
OTP_EXPIRY = 300  # 5 minutes

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# OTP Helper Functions
def generate_otp():
    """Generate a 6-digit OTP"""
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def store_otp(email, otp_type='register'):
    """Store OTP for an email address"""
    otp = generate_otp()
    OTP_STORAGE[email] = {
        'otp': otp,
        'timestamp': time.time(),
        'verified': False,
        'type': otp_type
    }
    return otp

def verify_otp(email, otp):
    """Verify OTP for an email address"""
    if email not in OTP_STORAGE:
        return False, "No OTP found. Please request a new OTP."
    
    stored_data = OTP_STORAGE[email]
    
    # Check if OTP is expired
    if time.time() - stored_data['timestamp'] > OTP_EXPIRY:
        del OTP_STORAGE[email]
        return False, "OTP has expired. Please request a new OTP."
    
    # Check if OTP matches
    if stored_data['otp'] != otp:
        return False, "Invalid OTP. Please try again."
    
    # Mark as verified
    OTP_STORAGE[email]['verified'] = True
    return True, "OTP verified successfully!"

def cleanup_expired_otps():
    """Remove expired OTPs from storage"""
    current_time = time.time()
    expired_emails = [email for email, data in OTP_STORAGE.items() 
                      if current_time - data['timestamp'] > OTP_EXPIRY]
    for email in expired_emails:
        del OTP_STORAGE[email]

def send_otp_email(recipient_email, otp, purpose='registration'):
    """Send OTP via SendGrid - SECURE email verification"""
    # Check if SendGrid is available and configured
    if not SENDGRID_AVAILABLE:
        print("WARNING: SendGrid library not installed! Run: pip install sendgrid")
        print(f"OTP for {recipient_email}: {otp}")
        return True, f"[DEMO MODE - SendGrid not installed] Your OTP is: {otp}"
    
    if not SENDGRID_API_KEY:
        print("WARNING: SENDGRID_API_KEY not configured in .env file!")
        print(f"OTP for {recipient_email}: {otp}")
        return True, f"[DEMO MODE - Email not configured] Your OTP is: {otp}"
    
    try:
        # Email content
        purpose_text = "registration" if purpose == 'register' else "login"
        subject = f'Your Textile Store Verification Code'
        
        # Professional HTML email body
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; text-align: center;">Textile Store</h2>
                    <h3 style="color: #666;">Verification Code</h3>
                    <p style="color: #666; font-size: 16px;">Hello,</p>
                    <p style="color: #666; font-size: 16px;">Your verification code for {purpose_text} is:</p>
                    <div style="background-color: #f0f0f0; padding: 20px; text-align: center; margin: 20px 0; border-radius: 5px;">
                        <h1 style="color: #333; margin: 0; font-size: 36px; letter-spacing: 5px;">{otp}</h1>
                    </div>
                    <p style="color: #999; font-size: 14px;">This code will expire in 5 minutes.</p>
                    <p style="color: #999; font-size: 14px;">If you didn't request this code, please ignore this email.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px; text-align: center;">Thank you for choosing Textile Store</p>
                </div>
            </body>
        </html>
        """
        
        # Plain text version for email clients that don't support HTML
        plain_content = f"""
Hello,

Your verification code for {purpose_text} at Textile Store is: {otp}

This code will expire in 5 minutes.

If you didn't request this code, please ignore this email.

Thank you,
Textile Store Team
        """
        
        # Create email message
        message = Mail(
            from_email=(SENDGRID_FROM_EMAIL, SENDGRID_FROM_NAME),
            to_emails=recipient_email,
            subject=subject,
            plain_text_content=plain_content,
            html_content=html_content
        )
        
        # Send email via SendGrid
        print(f"Sending OTP email to {recipient_email} via SendGrid...")
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"SUCCESS: OTP email sent via SendGrid to {recipient_email} (Status: {response.status_code})")
        return True, "OTP sent to your email! Please check your inbox (and spam folder)."
        
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR sending email via SendGrid: {error_msg}")
        print(f"OTP for demo purposes: {otp}")
        
        # Provide helpful error messages
        if "401" in error_msg or "Unauthorized" in error_msg:
            return True, f"[Email config error - Wrong API Key] Your OTP is: {otp}"
        elif "403" in error_msg or "Forbidden" in error_msg:
            return True, f"[Email config error - Verify sender email] Your OTP is: {otp}"
        else:
            return True, f"[Email failed - Demo Mode] Your OTP is: {otp}"

# Database initialization
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Create products table with enhanced fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            price REAL NOT NULL,
            description TEXT,
            images TEXT,
            stock INTEGER DEFAULT 0,
            sizes TEXT,
            colors TEXT,
            gender TEXT,
            has_variants BOOLEAN DEFAULT 0
        )
    ''')
    
    # Create product_variants table for color/model variations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            variant_name TEXT NOT NULL,
            variant_type TEXT DEFAULT 'color',
            price REAL,
            stock INTEGER DEFAULT 0,
            sku TEXT,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
        )
    ''')
    
    # Create variant_images table for multiple images per variant
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS variant_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            variant_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            display_order INTEGER DEFAULT 0,
            is_primary BOOLEAN DEFAULT 0,
            alt_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (variant_id) REFERENCES product_variants (id) ON DELETE CASCADE
        )
    ''')
    
    # Create cart table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Create orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT DEFAULT 'pending',
            shipping_address TEXT,
            phone_number TEXT,
            order_status TEXT DEFAULT 'processing',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create order_items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Create wishlist table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id),
            UNIQUE(user_id, product_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        if not user or not user[0]:
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products LIMIT 6')
    featured_products = cursor.fetchall()
    conn.close()
    return render_template('index.html', products=featured_products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Step 1: Verify credentials and send OTP
        if 'send_otp' in request.form:
            email = request.form['email']
            password = request.form['password']
            
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, password, is_admin FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            conn.close()
            
            if not user or not check_password_hash(user[2], password):
                flash('Invalid email or password.', 'error')
                return render_template('login.html')
            
            # Check if user is admin - skip OTP for admins
            if user[3]:  # is_admin
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                session['is_admin'] = user[3]
                flash('✅ Admin login successful! (OTP skipped for admin)', 'success')
                return redirect(url_for('index'))
            
            # For regular users, send OTP
            session['login_data'] = {
                'user_id': user[0],
                'user_name': user[1],
                'is_admin': user[3],
                'email': email
            }
            
            # Generate and store OTP
            otp = store_otp(email, 'login')
            cleanup_expired_otps()
            
            # Send OTP via email
            success, message = send_otp_email(email, otp, 'login')
            
            # Always show OTP on screen in green box
            flash(f'{message}', 'success')
            
            return render_template('login.html', show_otp_field=True, email=email)
        
        # Step 2: Verify OTP and complete login
        elif 'verify_otp' in request.form:
            otp = request.form['otp']
            
            if 'login_data' not in session:
                flash('Session expired. Please login again.', 'error')
                return redirect(url_for('login'))
            
            login_data = session['login_data']
            email = login_data['email']
            
            # Verify OTP
            success, message = verify_otp(email, otp)
            
            if not success:
                flash(message, 'error')
                return render_template('login.html', show_otp_field=True, email=email)
            
            # OTP verified - complete login
            session['user_id'] = login_data['user_id']
            session['user_name'] = login_data['user_name']
            session['is_admin'] = login_data['is_admin']
            
            # Clear OTP and login data
            if email in OTP_STORAGE:
                del OTP_STORAGE[email]
            session.pop('login_data', None)
            
            flash('✅ Login successful! OTP verified.', 'success')
            return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # DEBUG: Print what's in the form
        print("=" * 50)
        print("FORM DATA RECEIVED:")
        print(f"request.form keys: {list(request.form.keys())}")
        print(f"request.form: {dict(request.form)}")
        print("=" * 50)
        
        # Step 1: Send OTP to email
        if 'send_otp' in request.form:
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form.get('confirm_password', '')
            
            # Server-side password validation
            import re
            
            # Check if passwords match
            if password != confirm_password:
                flash('Passwords do not match!', 'error')
                return render_template('register.html')
            
            # Check password requirements
            if len(password) < 8:
                flash('Password must be at least 8 characters long!', 'error')
                return render_template('register.html')
            
            if not re.search(r'[A-Z]', password):
                flash('Password must contain at least one uppercase letter!', 'error')
                return render_template('register.html')
            
            if not re.search(r'[a-z]', password):
                flash('Password must contain at least one lowercase letter!', 'error')
                return render_template('register.html')
            
            if not re.search(r'[0-9]', password):
                flash('Password must contain at least one number!', 'error')
                return render_template('register.html')
            
            if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;\'`~]', password):
                flash('Password must contain at least one special character (!@#$%^&* etc.)!', 'error')
                return render_template('register.html')
            
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                flash('Email already registered.', 'error')
                conn.close()
                return render_template('register.html')
            conn.close()
            
            # Store registration data in session temporarily
            session['register_data'] = {
                'name': name,
                'email': email,
                'password': password
            }
            
            # Generate and store OTP
            otp = store_otp(email, 'register')
            cleanup_expired_otps()
            
            # Send OTP via email
            success, message = send_otp_email(email, otp, 'register')
            
            # Always show OTP on screen in green box
            flash(f'{message}', 'success')
            
            return render_template('register.html', show_otp_field=True, email=email)
        
        # Step 2: Verify OTP and complete registration
        elif 'verify_otp' in request.form:
            otp = request.form['otp']
            
            if 'register_data' not in session:
                flash('Session expired. Please start registration again.', 'error')
                return redirect(url_for('register'))
            
            reg_data = session['register_data']
            email = reg_data['email']
            
            # Verify OTP
            success, message = verify_otp(email, otp)
            
            if not success:
                flash(message, 'error')
                return render_template('register.html', show_otp_field=True, email=email)
            
            # OTP verified - complete registration
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            
            hashed_password = generate_password_hash(reg_data['password'])
            cursor.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', 
                          (reg_data['name'], email, hashed_password))
            conn.commit()
            conn.close()
            
            # Clear OTP and session data
            if email in OTP_STORAGE:
                del OTP_STORAGE[email]
            session.pop('register_data', None)
            
            flash('✅ Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        if 'send_otp' in request.form:
            # Step 1: Send OTP to email
            email = request.form['email']
            
            # Check if user exists
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                flash('No account found with this email address.', 'error')
                return render_template('forgot_password.html')
            
            # Generate and send OTP
            otp = str(random.randint(100000, 999999))
            OTP_STORAGE[email] = {
                'otp': otp,
                'expires': time.time() + 300,
                'purpose': 'forgot_password'
            }
            
            success, message = send_otp_email(email, otp, 'password reset')
            flash(message, 'success' if success else 'warning')
            
            # Store email in session
            session['reset_email'] = email
            
            return render_template('forgot_password.html', show_otp_field=True, email=email)
        
        elif 'verify_otp' in request.form:
            # Step 2: Verify OTP and show password reset form
            email = session.get('reset_email')
            entered_otp = request.form['otp']
            
            if not email or email not in OTP_STORAGE:
                flash('Session expired. Please try again.', 'error')
                return redirect(url_for('forgot_password'))
            
            stored_data = OTP_STORAGE[email]
            
            if time.time() > stored_data['expires']:
                flash('OTP expired. Please request a new one.', 'error')
                del OTP_STORAGE[email]
                return redirect(url_for('forgot_password'))
            
            if entered_otp != stored_data['otp']:
                flash('Invalid OTP. Please try again.', 'error')
                return render_template('forgot_password.html', show_otp_field=True, email=email)
            
            # OTP verified - show password reset form
            return render_template('forgot_password.html', show_password_field=True, email=email)
        
        elif 'reset_password' in request.form:
            # Step 3: Reset the password
            email = session.get('reset_email')
            new_password = request.form['new_password']
            confirm_password = request.form.get('confirm_password', '')
            
            import re
            
            # Validate password
            if new_password != confirm_password:
                flash('Passwords do not match!', 'error')
                return render_template('forgot_password.html', show_password_field=True, email=email)
            
            if len(new_password) < 8:
                flash('Password must be at least 8 characters long!', 'error')
                return render_template('forgot_password.html', show_password_field=True, email=email)
            
            if not re.search(r'[A-Z]', new_password):
                flash('Password must contain at least one uppercase letter!', 'error')
                return render_template('forgot_password.html', show_password_field=True, email=email)
            
            if not re.search(r'[a-z]', new_password):
                flash('Password must contain at least one lowercase letter!', 'error')
                return render_template('forgot_password.html', show_password_field=True, email=email)
            
            if not re.search(r'[0-9]', new_password):
                flash('Password must contain at least one number!', 'error')
                return render_template('forgot_password.html', show_password_field=True, email=email)
            
            if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;\'`~]', new_password):
                flash('Password must contain at least one special character!', 'error')
                return render_template('forgot_password.html', show_password_field=True, email=email)
            
            # Update password in database
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            hashed_password = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password = ? WHERE email = ?', (hashed_password, email))
            conn.commit()
            conn.close()
            
            # Clear OTP and session
            if email in OTP_STORAGE:
                del OTP_STORAGE[email]
            session.pop('reset_email', None)
            
            flash('Password reset successful! You can now login with your new password.', 'success')
            return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        user_id = session['user_id']
        
        if 'update_name' in request.form:
            # Update name
            new_name = request.form['name']
            
            if not new_name or len(new_name.strip()) < 2:
                flash('Name must be at least 2 characters long!', 'error')
                return redirect(url_for('profile'))
            
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET name = ? WHERE id = ?', (new_name, user_id))
            conn.commit()
            conn.close()
            
            session['user_name'] = new_name
            flash('Name updated successfully!', 'success')
            return redirect(url_for('profile'))
        
        elif 'update_password' in request.form:
            # Update password
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form.get('confirm_password', '')
            
            # Verify current password
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT password FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            conn.close()
            
            if not user or not check_password_hash(user[0], current_password):
                flash('Current password is incorrect!', 'error')
                return redirect(url_for('profile'))
            
            import re
            
            # Validate new password
            if new_password != confirm_password:
                flash('New passwords do not match!', 'error')
                return redirect(url_for('profile'))
            
            if len(new_password) < 8:
                flash('Password must be at least 8 characters long!', 'error')
                return redirect(url_for('profile'))
            
            if not re.search(r'[A-Z]', new_password):
                flash('Password must contain at least one uppercase letter!', 'error')
                return redirect(url_for('profile'))
            
            if not re.search(r'[a-z]', new_password):
                flash('Password must contain at least one lowercase letter!', 'error')
                return redirect(url_for('profile'))
            
            if not re.search(r'[0-9]', new_password):
                flash('Password must contain at least one number!', 'error')
                return redirect(url_for('profile'))
            
            if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;\'`~]', new_password):
                flash('Password must contain at least one special character!', 'error')
                return redirect(url_for('profile'))
            
            # Update password
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            hashed_password = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user_id))
            conn.commit()
            conn.close()
            
            flash('Password updated successfully!', 'success')
            return redirect(url_for('profile'))
    
    # Get user data
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, email FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    
    return render_template('profile.html', user={'name': user[0], 'email': user[1]})

@app.route('/products')
def products():
    category = request.args.get('category', '')
    gender = request.args.get('gender', '')
    size = request.args.get('size', '')
    color = request.args.get('color', '')
    search = request.args.get('search', '')
    price_range = request.args.get('price_range', '')
    sort = request.args.get('sort', '')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    
    if gender:
        query += ' AND gender = ?'
        params.append(gender)
    
    if size:
        query += ' AND sizes LIKE ?'
        params.append(f'%{size}%')
    
    if color:
        query += ' AND colors LIKE ?'
        params.append(f'%{color}%')
    
    if search:
        query += ' AND (name LIKE ? OR description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    # Price range filter
    if price_range:
        if price_range == '0-500':
            query += ' AND price < 500'
        elif price_range == '500-1000':
            query += ' AND price BETWEEN 500 AND 1000'
        elif price_range == '1000-2000':
            query += ' AND price BETWEEN 1000 AND 2000'
        elif price_range == '2000-5000':
            query += ' AND price BETWEEN 2000 AND 5000'
        elif price_range == '5000+':
            query += ' AND price > 5000'
    
    # Sorting
    if sort == 'name_asc':
        query += ' ORDER BY name ASC'
    elif sort == 'name_desc':
        query += ' ORDER BY name DESC'
    elif sort == 'price_asc':
        query += ' ORDER BY price ASC'
    elif sort == 'price_desc':
        query += ' ORDER BY price DESC'
    elif sort == 'newest':
        query += ' ORDER BY id DESC'
    else:
        query += ' ORDER BY name'
    
    cursor.execute(query, params)
    products = cursor.fetchall()
    
    # Get unique values for filters
    cursor.execute('SELECT DISTINCT category FROM products WHERE category IS NOT NULL')
    categories = [row[0] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT gender FROM products WHERE gender IS NOT NULL')
    genders = [row[0] for row in cursor.fetchall()]
    
    # Get all available sizes and colors
    cursor.execute('SELECT DISTINCT sizes FROM products WHERE sizes IS NOT NULL')
    all_sizes = set()
    for row in cursor.fetchall():
        if row[0]:
            all_sizes.update(row[0].split(','))
    sizes = sorted(list(all_sizes))
    
    cursor.execute('SELECT DISTINCT colors FROM products WHERE colors IS NOT NULL')
    all_colors = set()
    for row in cursor.fetchall():
        if row[0]:
            all_colors.update(row[0].split(','))
    colors = sorted(list(all_colors))
    
    conn.close()
    return render_template('product.html', products=products, categories=categories, 
                          genders=genders, sizes=sizes, colors=colors,
                          selected_category=category, selected_gender=gender,
                          selected_size=size, selected_color=color, search_term=search,
                          selected_price_range=price_range, selected_sort=sort)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Product detail page with variant support"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get product details
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('products'))
    
    # Check if product has variants
    has_variants = product[11] if len(product) > 11 else False
    
    variants_data = []
    if has_variants:
        # Get all variants with their images
        cursor.execute('''
            SELECT id, variant_name, variant_type, price, stock, sku, display_order
            FROM product_variants
            WHERE product_id = ?
            ORDER BY display_order, id
        ''', (product_id,))
        variants = cursor.fetchall()
        
        for variant in variants:
            variant_id = variant[0]
            
            # Get images for this variant
            cursor.execute('''
                SELECT id, image_path, display_order, is_primary, alt_text
                FROM variant_images
                WHERE variant_id = ?
                ORDER BY display_order, id
            ''', (variant_id,))
            images = cursor.fetchall()
            
            variants_data.append({
                'id': variant[0],
                'name': variant[1],
                'type': variant[2],
                'price': variant[3] if variant[3] else product[4],  # Use variant price or product price
                'stock': variant[4],
                'sku': variant[5],
                'display_order': variant[6],
                'images': [{
                    'id': img[0],
                    'path': img[1],
                    'order': img[2],
                    'is_primary': img[3],
                    'alt_text': img[4] or variant[1]
                } for img in images]
            })
    
    conn.close()
    return render_template('product_detail.html', product=product, 
                          has_variants=has_variants, variants=variants_data)

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    product_id = request.form['product_id']
    quantity = int(request.form['quantity'])
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check if item already in cart
    cursor.execute('SELECT id, quantity FROM cart WHERE user_id = ? AND product_id = ?', 
                   (session['user_id'], product_id))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute('UPDATE cart SET quantity = quantity + ? WHERE id = ?', 
                      (quantity, existing[0]))
    else:
        cursor.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)', 
                      (session['user_id'], product_id, quantity))
    
    conn.commit()
    conn.close()
    
    flash('Product added to cart!', 'success')
    return redirect(url_for('products'))

@app.route('/cart')
@login_required
def cart():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, p.name, p.price, c.quantity, p.images, p.id as product_id
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (session['user_id'],))
    cart_items = cursor.fetchall()
    conn.close()
    
    # Calculate total with proper type conversion
    total = 0.0
    for item in cart_items:
        try:
            price = float(item[2]) if item[2] else 0.0
            quantity = int(item[3]) if item[3] else 0
            total += price * quantity
        except (ValueError, TypeError):
            continue
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    cart_id = request.form['cart_id']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cart WHERE id = ? AND user_id = ?', 
                   (cart_id, session['user_id']))
    conn.commit()
    conn.close()
    
    flash('Item removed from cart.', 'info')
    return redirect(url_for('cart'))

@app.route('/toggle_wishlist', methods=['POST'])
@login_required
def toggle_wishlist():
    data = request.get_json()
    product_id = data.get('product_id')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check if item already in wishlist
    cursor.execute('SELECT id FROM wishlist WHERE user_id = ? AND product_id = ?', 
                   (session['user_id'], product_id))
    existing = cursor.fetchone()
    
    if existing:
        # Remove from wishlist
        cursor.execute('DELETE FROM wishlist WHERE id = ?', (existing[0],))
        conn.commit()
        conn.close()
        return jsonify({'status': 'removed', 'message': 'Removed from wishlist'})
    else:
        # Add to wishlist
        cursor.execute('INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)', 
                      (session['user_id'], product_id))
        conn.commit()
        conn.close()
        return jsonify({'status': 'added', 'message': 'Added to wishlist'})

@app.route('/wishlist')
@login_required
def wishlist():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT w.id, p.id, p.name, p.price, p.images, p.category, p.description
        FROM wishlist w
        JOIN products p ON w.product_id = p.id
        WHERE w.user_id = ?
        ORDER BY w.added_date DESC
    ''', (session['user_id'],))
    wishlist_items = cursor.fetchall()
    conn.close()
    
    return render_template('wishlist.html', wishlist_items=wishlist_items)

@app.route('/get_wishlist_status/<int:product_id>')
@login_required
def get_wishlist_status(product_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM wishlist WHERE user_id = ? AND product_id = ?', 
                   (session['user_id'], product_id))
    existing = cursor.fetchone()
    conn.close()
    
    return jsonify({'in_wishlist': existing is not None})

@app.route('/admin')
@admin_required
def admin():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products ORDER BY name')
    products = cursor.fetchall()
    conn.close()
    return render_template('admin.html', products=products)

@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    from datetime import datetime, timedelta
    
    # Get time period filter (default: month)
    period = request.args.get('period', 'month')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Calculate date range based on period
    today = datetime.now()
    if period == 'week':
        start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        period_label = 'Last 7 Days'
    elif period == 'month':
        start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        period_label = 'Last 30 Days'
    elif period == 'year':
        start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
        period_label = 'Last 365 Days'
    else:  # all time
        start_date = '2000-01-01'
        period_label = 'All Time'
    
    # Get total sales
    cursor.execute('''
        SELECT COUNT(*), SUM(total_amount) 
        FROM orders 
        WHERE order_date >= ? AND order_status != 'cancelled'
    ''', (start_date,))
    sales_data = cursor.fetchone()
    total_orders = sales_data[0] or 0
    total_revenue = sales_data[1] or 0
    
    # Get total products sold
    cursor.execute('''
        SELECT SUM(oi.quantity) 
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE o.order_date >= ? AND o.order_status != 'cancelled'
    ''', (start_date,))
    total_products_sold = cursor.fetchone()[0] or 0
    
    # Calculate average order value
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    # Get sales by status
    cursor.execute('''
        SELECT order_status, COUNT(*), SUM(total_amount)
        FROM orders
        WHERE order_date >= ?
        GROUP BY order_status
    ''', (start_date,))
    status_stats = cursor.fetchall()
    
    # Get top selling products
    cursor.execute('''
        SELECT p.name, SUM(oi.quantity) as total_qty, SUM(oi.quantity * oi.price) as total_revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.order_date >= ? AND o.order_status != 'cancelled'
        GROUP BY p.id, p.name
        ORDER BY total_qty DESC
        LIMIT 5
    ''', (start_date,))
    top_products = cursor.fetchall()
    
    # Get daily sales for chart (last 30 days)
    cursor.execute('''
        SELECT DATE(order_date) as date, COUNT(*) as orders, SUM(total_amount) as revenue
        FROM orders
        WHERE order_date >= ? AND order_status != 'cancelled'
        GROUP BY DATE(order_date)
        ORDER BY date
    ''', (start_date,))
    daily_sales = cursor.fetchall()
    
    # Get revenue by category
    cursor.execute('''
        SELECT p.category, SUM(oi.quantity * oi.price) as revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.order_date >= ? AND o.order_status != 'cancelled'
        GROUP BY p.category
        ORDER BY revenue DESC
    ''', (start_date,))
    category_revenue = cursor.fetchall()
    
    # Get recent orders
    cursor.execute('''
        SELECT o.id, u.name, o.total_amount, o.order_status, o.order_date
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.order_date >= ?
        ORDER BY o.order_date DESC
        LIMIT 10
    ''', (start_date,))
    recent_orders = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin_analytics.html',
                          period=period,
                          period_label=period_label,
                          total_orders=total_orders,
                          total_revenue=total_revenue,
                          total_products_sold=total_products_sold,
                          avg_order_value=avg_order_value,
                          status_stats=status_stats,
                          top_products=top_products,
                          daily_sales=daily_sales,
                          category_revenue=category_revenue,
                          recent_orders=recent_orders)

@app.route('/admin/upload_image', methods=['POST'])
@admin_required
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        # Create unique filename with timestamp
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        unique_filename = timestamp + filename
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        return jsonify({'filename': unique_filename, 'success': True}), 200
    
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/admin/delete_image', methods=['POST'])
@admin_required
def delete_image():
    data = request.get_json()
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return jsonify({'success': True}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'File not found'}), 404

# ===== PRODUCT VARIANT MANAGEMENT ROUTES =====

@app.route('/api/product/<int:product_id>/variants')
def get_product_variants(product_id):
    """Get all variants and their images for a product"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get product info
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        conn.close()
        return jsonify({'error': 'Product not found'}), 404
    
    # Get variants
    cursor.execute('''
        SELECT id, variant_name, variant_type, price, stock, sku, display_order
        FROM product_variants
        WHERE product_id = ?
        ORDER BY display_order, id
    ''', (product_id,))
    variants = cursor.fetchall()
    
    result = []
    for variant in variants:
        variant_id = variant[0]
        
        # Get images for this variant
        cursor.execute('''
            SELECT id, image_path, display_order, is_primary, alt_text
            FROM variant_images
            WHERE variant_id = ?
            ORDER BY display_order, id
        ''', (variant_id,))
        images = cursor.fetchall()
        
        result.append({
            'id': variant[0],
            'name': variant[1],
            'type': variant[2],
            'price': variant[3],
            'stock': variant[4],
            'sku': variant[5],
            'display_order': variant[6],
            'images': [{
                'id': img[0],
                'path': img[1],
                'order': img[2],
                'is_primary': img[3],
                'alt_text': img[4]
            } for img in images]
        })
    
    conn.close()
    return jsonify({'variants': result})

@app.route('/admin/product/<int:product_id>/add_variant', methods=['POST'])
@admin_required
def add_variant(product_id):
    """Add a new variant to a product"""
    data = request.get_json()
    
    variant_name = data.get('variant_name')
    variant_type = data.get('variant_type', 'color')
    price = data.get('price')
    stock = data.get('stock', 0)
    sku = data.get('sku', '')
    display_order = data.get('display_order', 0)
    
    if not variant_name:
        return jsonify({'error': 'Variant name is required'}), 400
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO product_variants (product_id, variant_name, variant_type, price, stock, sku, display_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (product_id, variant_name, variant_type, price, stock, sku, display_order))
        
        variant_id = cursor.lastrowid
        
        # Update product to have_variants flag
        cursor.execute('UPDATE products SET has_variants = 1 WHERE id = ?', (product_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'variant_id': variant_id}), 200
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/variant/<int:variant_id>/edit', methods=['POST'])
@admin_required
def edit_variant(variant_id):
    """Edit an existing variant"""
    data = request.get_json()
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    try:
        updates = []
        params = []
        
        if 'variant_name' in data:
            updates.append('variant_name = ?')
            params.append(data['variant_name'])
        if 'variant_type' in data:
            updates.append('variant_type = ?')
            params.append(data['variant_type'])
        if 'price' in data:
            updates.append('price = ?')
            params.append(data['price'])
        if 'stock' in data:
            updates.append('stock = ?')
            params.append(data['stock'])
        if 'sku' in data:
            updates.append('sku = ?')
            params.append(data['sku'])
        if 'display_order' in data:
            updates.append('display_order = ?')
            params.append(data['display_order'])
        
        if not updates:
            return jsonify({'error': 'No fields to update'}), 400
        
        params.append(variant_id)
        query = f"UPDATE product_variants SET {', '.join(updates)} WHERE id = ?"
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        return jsonify({'success': True}), 200
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/variant/<int:variant_id>/delete', methods=['POST'])
@admin_required
def delete_variant(variant_id):
    """Delete a variant and all its images"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    try:
        # Get all images for this variant
        cursor.execute('SELECT image_path FROM variant_images WHERE variant_id = ?', (variant_id,))
        images = cursor.fetchall()
        
        # Delete image files
        for img in images:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], img[0])
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
        
        # Delete variant (cascade will delete images from DB)
        cursor.execute('DELETE FROM product_variants WHERE id = ?', (variant_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True}), 200
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/variant/<int:variant_id>/upload_image', methods=['POST'])
@admin_required
def upload_variant_image(variant_id):
    """Upload an image for a variant"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to filename to make it unique
        timestamp = str(int(time.time()))
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{timestamp}{ext}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Get the current max display order
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(display_order) FROM variant_images WHERE variant_id = ?', (variant_id,))
        max_order = cursor.fetchone()[0]
        display_order = (max_order or 0) + 1
        
        # Save to database
        is_primary = request.form.get('is_primary', 'false') == 'true'
        alt_text = request.form.get('alt_text', '')
        
        cursor.execute('''
            INSERT INTO variant_images (variant_id, image_path, display_order, is_primary, alt_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (variant_id, filename, display_order, is_primary, alt_text))
        
        image_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'filename': filename,
            'image_id': image_id,
            'display_order': display_order
        }), 200
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/admin/variant/image/<int:image_id>/delete', methods=['POST'])
@admin_required
def delete_variant_image(image_id):
    """Delete a variant image"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    try:
        # Get image path
        cursor.execute('SELECT image_path FROM variant_images WHERE id = ?', (image_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'error': 'Image not found'}), 404
        
        image_path = result[0]
        
        # Delete file
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], image_path)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
        
        # Delete from database
        cursor.execute('DELETE FROM variant_images WHERE id = ?', (image_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True}), 200
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/variant/image/<int:image_id>/reorder', methods=['POST'])
@admin_required
def reorder_variant_image(image_id):
    """Reorder variant images"""
    data = request.get_json()
    new_order = data.get('display_order')
    
    if new_order is None:
        return jsonify({'error': 'display_order is required'}), 400
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE variant_images SET display_order = ? WHERE id = ?', (new_order, image_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True}), 200
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

# ===== END VARIANT MANAGEMENT ROUTES =====

# ===== AMAZON-STYLE PRODUCT PAGE =====

@app.route('/amazon-product/<int:product_id>')
def amazon_product_page(product_id):
    """Amazon-style product detail page with hover zoom and carousel"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get product details
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        flash('Product not found', 'error')
        conn.close()
        return redirect(url_for('products'))
    
    # Get related products (same category, exclude current product)
    cursor.execute('''
        SELECT * FROM products 
        WHERE category = ? AND id != ? 
        LIMIT 8
    ''', (product[2], product_id))
    related_products = cursor.fetchall()
    
    conn.close()
    
    return render_template('amazon_style_product.html', 
                          product=product,
                          related_products=related_products)

# ===== END AMAZON-STYLE PRODUCT PAGE =====

@app.route('/admin/add_product', methods=['POST'])
@admin_required
def add_product():
    name = request.form['name']
    category = request.form['category']
    subcategory = request.form.get('subcategory', '')
    gender = request.form.get('gender', '')
    price = float(request.form['price'])
    description = request.form['description']
    stock = int(request.form['stock'])
    images = request.form.get('images', 'tshirt.jpg')  # Comma-separated image filenames
    sizes = request.form.get('sizes', '')
    colors = request.form.get('colors', '')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO products (name, category, subcategory, gender, price, description, images, stock, sizes, colors)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, category, subcategory, gender, price, description, images, stock, sizes, colors))
    conn.commit()
    conn.close()
    
    flash('Product added successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/edit_product', methods=['POST'])
@admin_required
def edit_product():
    product_id = request.form['product_id']
    name = request.form['name']
    category = request.form['category']
    subcategory = request.form.get('subcategory', '')
    gender = request.form.get('gender', '')
    price = float(request.form['price'])
    description = request.form['description']
    stock = int(request.form['stock'])
    images = request.form.get('images', 'tshirt.jpg')  # Comma-separated image filenames
    sizes = request.form.get('sizes', '')
    colors = request.form.get('colors', '')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE products 
        SET name = ?, category = ?, subcategory = ?, gender = ?, price = ?, description = ?, images = ?, stock = ?, sizes = ?, colors = ?
        WHERE id = ?
    ''', (name, category, subcategory, gender, price, description, images, stock, sizes, colors, product_id))
    conn.commit()
    conn.close()
    
    flash('Product updated successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete_product', methods=['POST'])
@admin_required
def delete_product():
    product_id = request.form['product_id']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/checkout')
@login_required
def checkout():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, p.name, p.price, c.quantity, p.images, p.id as product_id
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (session['user_id'],))
    cart_items = cursor.fetchall()
    conn.close()
    
    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('cart'))
    
    # Calculate total with proper type conversion
    total = 0.0
    for item in cart_items:
        try:
            price = float(item[2]) if item[2] else 0.0
            quantity = int(item[3]) if item[3] else 0
            total += price * quantity
        except (ValueError, TypeError):
            continue
    
    return render_template('checkout.html', cart_items=cart_items, total=total)

@app.route('/create_mock_payment', methods=['POST'])
@login_required
def create_mock_payment():
    """Create mock payment order - No external service needed!"""
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        payment_method = data.get('payment_method', 'UPI')
        
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Invalid amount'}), 400
        
        # Generate mock order ID
        import random
        import string
        mock_order_id = 'order_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=14))
        
        return jsonify({
            'success': True,
            'order_id': mock_order_id,
            'amount': amount,
            'currency': 'INR',
            'payment_method': payment_method
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/simulate_payment', methods=['POST'])
@login_required
def simulate_payment():
    """Simulate payment completion - Mock system"""
    try:
        data = request.get_json()
        
        order_id = data.get('order_id')
        payment_method = data.get('payment_method')
        success = data.get('success', True)  # Can simulate failures
        
        if success:
            # Generate mock payment ID
            import random
            import string
            payment_id = 'pay_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=14))
            
            return jsonify({
                'success': True,
                'message': 'Payment successful!',
                'payment_id': payment_id,
                'order_id': order_id,
                'payment_method': payment_method
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Payment failed'
            }), 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    try:
        payment_method = request.form.get('payment_method')
        shipping_address = request.form.get('shipping_address')
        phone_number = request.form.get('phone_number')
        mock_payment_id = request.form.get('mock_payment_id', '')
        mock_order_id = request.form.get('mock_order_id', '')
        
        # Validate required fields
        if not payment_method:
            flash('Please select a payment method.', 'error')
            return redirect(url_for('checkout'))
        
        if not shipping_address or not phone_number:
            flash('Please provide shipping address and phone number.', 'error')
            return redirect(url_for('checkout'))
        
        # Get cart items
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.id, p.id as product_id, p.name, p.price, c.quantity
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?
        ''', (session['user_id'],))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            conn.close()
            flash('Your cart is empty!', 'error')
            return redirect(url_for('cart'))
        
        # Calculate total with proper type conversion
        total_amount = 0.0
        for item in cart_items:
            price = float(item[3]) if item[3] else 0.0
            quantity = int(item[4]) if item[4] else 0
            total_amount += price * quantity
        
        # Create order
        cursor.execute('''
            INSERT INTO orders (user_id, total_amount, payment_method, shipping_address, phone_number)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['user_id'], total_amount, payment_method, shipping_address, phone_number))
        
        order_id = cursor.lastrowid
        
        # Add order items
        for item in cart_items:
            cursor.execute('''
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
            ''', (order_id, item[1], item[4], item[3]))
            
            # Update stock
            cursor.execute('''
                UPDATE products SET stock = stock - ? WHERE id = ?
            ''', (item[4], item[1]))
        
        # Clear cart
        cursor.execute('DELETE FROM cart WHERE user_id = ?', (session['user_id'],))
        
        conn.commit()
        conn.close()
        
        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_confirmation', order_id=order_id))
    
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        flash(f'An error occurred while processing your payment: {str(e)}', 'error')
        return redirect(url_for('checkout'))

@app.route('/order_confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT o.*, oi.product_id, p.name, oi.quantity, oi.price
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        WHERE o.id = ? AND o.user_id = ?
    ''', (order_id, session['user_id']))
    order_details = cursor.fetchall()
    conn.close()
    
    if not order_details:
        flash('Order not found!', 'error')
        return redirect(url_for('index'))
    
    return render_template('order_confirmation.html', order_details=order_details, order_id=order_id)

@app.route('/orders')
@login_required
def orders():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, order_date, total_amount, payment_method, order_status
        FROM orders WHERE user_id = ? ORDER BY order_date DESC
    ''', (session['user_id'],))
    user_orders = cursor.fetchall()
    conn.close()
    
    return render_template('orders.html', orders=user_orders)

@app.route('/download_bill/<int:order_id>')
@login_required
def download_bill(order_id):
    if not REPORTLAB_AVAILABLE:
        flash('PDF generation is not available. Please install ReportLab.', 'error')
        return redirect(url_for('orders'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get order details
    cursor.execute('''
        SELECT o.*, u.name as customer_name, u.email
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.id = ? AND o.user_id = ?
    ''', (order_id, session['user_id']))
    order = cursor.fetchone()
    
    if not order:
        flash('Order not found!', 'error')
        return redirect(url_for('orders'))
    
    # Get order items
    cursor.execute('''
        SELECT p.name, oi.quantity, oi.price
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', (order_id,))
    items = cursor.fetchall()
    
    conn.close()
    
    # Generate PDF bill
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1
    )
    
    # Title
    story.append(Paragraph("TEXTILE STORE", title_style))
    story.append(Paragraph("INVOICE", styles['Heading2']))
    story.append(Spacer(1, 20))
    
    # Order info
    order_info = [
        ['Invoice No:', f'#{order[0]}'],
        ['Date:', order[2]],
        ['Customer:', order[7]],
        ['Email:', order[8]],
        ['Payment Method:', order[4]],
        ['Status:', order[8]]
    ]
    
    order_table = Table(order_info, colWidths=[2*inch, 3*inch])
    order_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(order_table)
    story.append(Spacer(1, 20))
    
    # Items table
    items_data = [['Product', 'Quantity', 'Price', 'Total']]
    total = 0
    for item in items:
        item_total = item[1] * item[2]
        total += item_total
        items_data.append([
            item[0],
            str(item[1]),
            f'${item[2]:.2f}',
            f'${item_total:.2f}'
        ])
    
    items_data.append(['', '', 'TOTAL:', f'${total:.2f}'])
    
    items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1*inch, 1*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(items_table)
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("Thank you for your business!", styles['Normal']))
    story.append(Paragraph("Textile Store - Quality Textiles for Every Need", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{order_id}.pdf'
    
    return response

@app.route('/admin/orders')
@admin_required
def admin_orders():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT o.id, o.order_date, o.total_amount, o.payment_method, o.order_status, 
               o.shipping_address, o.phone_number, u.name as customer_name, u.email
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.order_date DESC
    ''')
    all_orders = cursor.fetchall()
    conn.close()
    
    return render_template('admin_orders.html', orders=all_orders)

@app.route('/admin/update_order_status', methods=['POST'])
@admin_required
def update_order_status():
    try:
        order_id = request.form.get('order_id')
        new_status = request.form.get('status')
        
        if not order_id or not new_status:
            flash('Order ID and status are required', 'error')
            return redirect(url_for('admin_orders'))
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE orders SET order_status = ? WHERE id = ?
        ''', (new_status, order_id))
        conn.commit()
        conn.close()
        
        flash(f'Order #{order_id} status updated to {new_status.replace("_", " ").title()}', 'success')
        return redirect(url_for('admin_orders'))
    except Exception as e:
        flash(f'Error updating order status: {str(e)}', 'error')
        return redirect(url_for('admin_orders'))

@app.route('/admin/update_order_status_detail', methods=['POST'])
@admin_required
def admin_update_order_status():
    try:
        order_id = request.form.get('order_id')
        new_status = request.form.get('status')
        
        if not order_id or not new_status:
            flash('Order ID and status are required', 'error')
            return redirect(url_for('admin_orders'))
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE orders SET order_status = ? WHERE id = ?
        ''', (new_status, order_id))
        conn.commit()
        conn.close()
        
        flash(f'Order #{order_id} status updated to {new_status.replace("_", " ").title()}!', 'success')
        return redirect(url_for('admin_order_details', order_id=order_id))
    except Exception as e:
        flash(f'Error updating order status: {str(e)}', 'error')
        return redirect(url_for('admin_orders'))

@app.route('/customer_order_details/<int:order_id>')
@login_required
def customer_order_details(order_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get order details for the logged-in user only
    cursor.execute('''
        SELECT o.id, o.user_id, o.order_date, o.total_amount, o.payment_method, 
               o.order_status, o.shipping_address, o.phone_number
        FROM orders o
        WHERE o.id = ? AND o.user_id = ?
    ''', (order_id, session['user_id']))
    order = cursor.fetchone()
    
    if not order:
        flash('Order not found!', 'error')
        return redirect(url_for('orders'))
    
    # Get order items
    cursor.execute('''
        SELECT p.name, p.category, oi.quantity, oi.price, p.images
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', (order_id,))
    items = cursor.fetchall()
    
    conn.close()
    
    return render_template('customer_order_details.html', order=order, items=items)

@app.route('/cancel_order/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check if order belongs to the user and is cancellable
    cursor.execute('''
        SELECT order_status FROM orders 
        WHERE id = ? AND user_id = ?
    ''', (order_id, session['user_id']))
    order = cursor.fetchone()
    
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'})
    
    if order[0] not in ['processing', 'confirmed']:
        return jsonify({'success': False, 'message': 'This order cannot be cancelled'})
    
    # Update order status to cancelled
    cursor.execute('''
        UPDATE orders SET order_status = 'cancelled' WHERE id = ?
    ''', (order_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/return_order/<int:order_id>', methods=['POST'])
@login_required
def return_order(order_id):
    data = request.get_json()
    reason = data.get('reason', '').strip()
    
    if not reason:
        return jsonify({'success': False, 'message': 'Return reason is required'})
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check if order belongs to the user and is delivered
    cursor.execute('''
        SELECT order_status FROM orders 
        WHERE id = ? AND user_id = ?
    ''', (order_id, session['user_id']))
    order = cursor.fetchone()
    
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'})
    
    if order[0] != 'delivered':
        return jsonify({'success': False, 'message': 'Only delivered orders can be returned'})
    
    # Create returns table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Insert return request
    cursor.execute('''
        INSERT INTO returns (order_id, user_id, reason)
        VALUES (?, ?, ?)
    ''', (order_id, session['user_id'], reason))
    
    # Update order status to indicate return requested
    cursor.execute('''
        UPDATE orders SET order_status = 'return_requested' WHERE id = ?
    ''', (order_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/admin/download_bill/<int:order_id>')
@admin_required
def admin_download_bill(order_id):
    if not REPORTLAB_AVAILABLE:
        flash('PDF generation is not available. Please install ReportLab.', 'error')
        return redirect(url_for('admin_orders'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get order details (no user_id check for admins)
    # Order: id, user_id, order_date, total_amount, payment_method, order_status, shipping_address, phone_number, customer_name, email
    cursor.execute('''
        SELECT o.id, o.user_id, o.order_date, o.total_amount, o.payment_method, 
               o.order_status, o.shipping_address, o.phone_number,
               u.name as customer_name, u.email
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.id = ?
    ''', (order_id,))
    order = cursor.fetchone()
    
    if not order:
        flash('Order not found!', 'error')
        return redirect(url_for('admin_orders'))
    
    # Get order items
    cursor.execute('''
        SELECT p.name, oi.quantity, oi.price
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', (order_id,))
    items = cursor.fetchall()
    
    conn.close()
    
    # Generate PDF bill
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1
    )
    
    # Title
    story.append(Paragraph("LUXE TEXTILE", title_style))
    story.append(Paragraph("INVOICE", styles['Heading2']))
    story.append(Spacer(1, 20))
    
    # Order info - indices: 0=id, 2=order_date, 8=customer_name, 9=email, 4=payment_method, 5=order_status
    order_info = [
        ['Invoice No:', f'#{order[0]}'],
        ['Date:', order[2]],
        ['Customer:', order[8]],
        ['Email:', order[9]],
        ['Phone:', order[7]],
        ['Payment Method:', order[4]],
        ['Status:', order[5].replace('_', ' ').title() if order[5] else 'Processing']
    ]
    
    order_table = Table(order_info, colWidths=[2*inch, 3*inch])
    order_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(order_table)
    story.append(Spacer(1, 20))
    
    # Shipping Address
    story.append(Paragraph("<b>Shipping Address:</b>", styles['Normal']))
    story.append(Paragraph(order[6], styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Items table
    items_data = [['Product', 'Quantity', 'Price', 'Total']]
    total = 0
    for item in items:
        item_total = item[1] * item[2]
        total += item_total
        items_data.append([
            item[0],
            str(item[1]),
            f'₹{item[2]:.2f}',
            f'₹{item_total:.2f}'
        ])
    
    items_data.append(['', '', 'TOTAL:', f'₹{total:.2f}'])
    
    items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1*inch, 1*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(items_table)
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("Thank you for your business!", styles['Normal']))
    story.append(Paragraph("LUXE TEXTILE - Premium Quality Textiles", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{order_id}.pdf'
    
    return response

@app.route('/admin/order_details/<int:order_id>')
@admin_required
def admin_order_details(order_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get order details - specify exact columns in expected order
    # Expected order: id, user_id, order_date, total_amount, payment_method, order_status, shipping_address, phone_number, customer_name, email
    cursor.execute('''
        SELECT o.id, o.user_id, o.order_date, o.total_amount, o.payment_method, 
               o.order_status, o.shipping_address, o.phone_number,
               u.name as customer_name, u.email
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.id = ?
    ''', (order_id,))
    order = cursor.fetchone()
    
    if not order:
        flash('Order not found!', 'error')
        return redirect(url_for('admin_orders'))
    
    # Get order items
    cursor.execute('''
        SELECT p.name, p.category, oi.quantity, oi.price, p.images
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', (order_id,))
    items = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin_order_details.html', order=order, items=items)

# Initialize database when app starts (important for Render deployment)
init_db()

# Add admin user if not exists
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Add admin user if not exists
cursor.execute('SELECT COUNT(*) FROM users WHERE email = ?', ('admin@textile.com',))
if cursor.fetchone()[0] == 0:
    admin_password = generate_password_hash('admin123')
    cursor.execute('''
        INSERT INTO users (name, email, password, is_admin)
        VALUES (?, ?, ?, ?)
    ''', ('Admin', 'admin@textile.com', admin_password, True))

conn.commit()
conn.close()

# Run app when called directly
if __name__ == '__main__':
    app.run(debug=True)
