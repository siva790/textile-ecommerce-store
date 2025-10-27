# 🛍️ Textile E-Commerce Store

A full-featured e-commerce web application for selling textile products built with Flask, featuring modern UI/UX, secure authentication, payment integration, and admin management.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## ✨ Features

### 🛒 Customer Features
- **User Authentication**
  - Email OTP verification for registration and login
  - Secure password requirements (uppercase, lowercase, numbers, special characters)
  - Password strength indicator
  - Forgot password functionality
  - Profile management (update name and password)

- **Product Browsing**
  - Advanced filtering (category, subcategory, gender, price range)
  - Search functionality
  - Product variants (sizes, colors)
  - Multiple product images support
  - Wishlist management
  
- **Shopping Experience**
  - Shopping cart with quantity management
  - Checkout process with customer details
  - Multiple payment options (GPay, PhonePe, Paytm, Credit/Debit Card, Cash on Delivery)
  - Mock payment system for testing
  - Order tracking and history
  - PDF invoice download

### 👨‍💼 Admin Features
- **Product Management**
  - Add/Edit/Delete products
  - Multiple image uploads per product
  - Variant management (sizes, colors)
  - Stock tracking
  - Category and subcategory organization

- **Order Management**
  - View all orders
  - Order status updates (Pending, Processing, Shipped, Delivered, Cancelled)
  - Detailed order information
  - Customer details

- **Analytics Dashboard**
  - Sales statistics (daily, weekly, monthly, yearly)
  - Revenue tracking
  - Top-selling products
  - Order status breakdown
  - Category revenue analysis
  - Interactive charts (Chart.js)

### 🔒 Security Features
- OTP-based email verification via SendGrid
- Password hashing (Werkzeug)
- Session management
- Admin access control
- CSRF protection

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- SendGrid account (for email OTP)
- Git (for version control)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/textile-store.git
cd textile-store
```

2. **Create a virtual environment**
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
# Copy the example env file
copy env.example .env  # Windows
# OR
cp env.example .env    # macOS/Linux

# Edit .env and add your credentials:
# - SECRET_KEY: Generate a random string
# - SENDGRID_API_KEY: Your SendGrid API key
# - SENDGRID_FROM_EMAIL: Your verified sender email
# - SENDGRID_FROM_NAME: Your store name
```

5. **Run the application**
```bash
python app.py
```

6. **Access the application**
```
http://127.0.0.1:5000
```

---

## 📋 Default Admin Credentials

```
Email: admin@textile.com
Password: admin123
```

**⚠️ IMPORTANT: Change these credentials after first login in production!**

---

## 🔧 Configuration

### SendGrid Setup
1. Sign up at [SendGrid](https://sendgrid.com/)
2. Verify your sender email address
3. Create an API key with "Mail Send" permissions
4. Add the API key to your `.env` file

See `SENDGRID_SETUP_GUIDE.md` for detailed instructions.

### Payment Integration
The app currently uses a **mock payment system** for testing. To integrate real payment gateways:
- **Razorpay**: See `RAZORPAY_SETUP_GUIDE.md`
- **Stripe**: Documentation coming soon
- **PayPal**: Documentation coming soon

---

## 📁 Project Structure

```
textile-store/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── database.db                 # SQLite database (auto-created)
├── .env                        # Environment variables (not in Git)
├── env.example                 # Environment variables template
├── .gitignore                  # Git ignore rules
│
├── static/                     # Static files
│   ├── css/
│   │   ├── style.css          # Main stylesheet
│   │   └── product-page.css   # Product page styles
│   ├── js/
│   │   ├── script.js          # Main JavaScript
│   │   └── product-page.js    # Product page scripts
│   └── images/                # Product images & assets
│
├── templates/                  # HTML templates (Jinja2)
│   ├── base.html              # Base template
│   ├── index.html             # Homepage
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── forgot_password.html   # Password reset
│   ├── profile.html           # User profile
│   ├── product.html           # Product listing
│   ├── product_detail.html    # Product details
│   ├── cart.html              # Shopping cart
│   ├── checkout.html          # Checkout page
│   ├── wishlist.html          # Wishlist
│   ├── orders.html            # Customer orders
│   ├── order_confirmation.html# Order success
│   ├── customer_order_details.html
│   ├── admin.html             # Admin dashboard
│   ├── admin_orders.html      # Order management
│   ├── admin_order_details.html
│   └── admin_analytics.html   # Analytics dashboard
│
└── Documentation/              # Setup guides & documentation
    ├── SENDGRID_SETUP_GUIDE.md
    ├── RAZORPAY_SETUP_GUIDE.md
    ├── IMAGE_UPLOAD_GUIDE.md
    ├── OTP_VERIFICATION_GUIDE.md
    ├── CATEGORY_SYSTEM.md
    ├── VARIANT_SYSTEM_GUIDE.md
    └── ORDER_TRACKING_FEATURES.md
```

---

## 🗄️ Database Schema

The application uses SQLite with the following tables:

- **users** - User accounts (customers & admin)
- **products** - Product catalog
- **cart** - Shopping cart items
- **wishlist** - User wishlists
- **orders** - Order records
- **order_items** - Order line items

Database is automatically initialized on first run.

---

## 🎨 Technology Stack

### Backend
- **Flask** - Python web framework
- **SQLite** - Database
- **SendGrid** - Email service
- **Werkzeug** - Password hashing & security
- **ReportLab** - PDF generation

### Frontend
- **HTML5/CSS3** - Structure & styling
- **Tailwind CSS** - Utility-first CSS framework
- **JavaScript** - Client-side interactivity
- **Chart.js** - Data visualization
- **Font Awesome** - Icons

### Key Libraries
```
Flask==3.0.0
sendgrid==6.11.0
reportlab==4.0.7
python-dotenv==1.0.0
Werkzeug==3.0.1
```

---

## 📝 Features Documentation

### OTP Email Verification
- OTP sent via SendGrid on registration/login
- 6-digit code, 5-minute expiration
- Email templates with HTML styling
- Fallback demo mode if email fails

### Password Security
- Minimum 8 characters
- Must include: uppercase, lowercase, number, special character
- Real-time strength indicator
- Confirm password validation
- Secure hashing with Werkzeug

### Product Variants
- Multiple sizes per product
- Multiple colors per product
- Dynamic pricing per variant
- Stock tracking per variant

### Payment System
- Mock payment for testing
- Multiple payment methods
- Order confirmation emails
- PDF invoice generation

### Analytics
- Time-period filtering (week/month/year/all)
- Revenue & profit tracking
- Top products analysis
- Order status breakdown
- Category performance
- Interactive charts

---

## 🧪 Testing

### Test Mock Payments
1. Add products to cart
2. Proceed to checkout
3. Select any payment method
4. Use mock payment to simulate success/failure
5. Download invoice PDF

### Test OTP System
1. Register new user with your email
2. Check email for OTP (including spam folder)
3. Verify OTP within 5 minutes
4. Test forgot password flow

### Admin Functions
1. Login as admin
2. Add products with images
3. Manage orders
4. View analytics dashboard
5. Update product stock

---

## 🚀 Deployment

### Production Checklist
- [ ] Change default admin password
- [ ] Generate strong `SECRET_KEY`
- [ ] Set up production SendGrid account
- [ ] Configure real payment gateway
- [ ] Use production WSGI server (Gunicorn/uWSGI)
- [ ] Set up PostgreSQL/MySQL (instead of SQLite)
- [ ] Enable HTTPS/SSL
- [ ] Set up backup system
- [ ] Configure error logging
- [ ] Set `DEBUG=False` in Flask

### Deployment Platforms
- **Heroku** - Easy deployment with free tier
- **PythonAnywhere** - Python-specific hosting
- **AWS/DigitalOcean** - Full control VPS
- **Render** - Modern cloud platform

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

Created with ❤️ by [Your Name]

---

## 📧 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Email: your.email@example.com

---

## 🙏 Acknowledgments

- Flask community for excellent documentation
- SendGrid for email services
- Tailwind CSS for beautiful UI components
- Chart.js for data visualization
- Font Awesome for icons

---

## 📸 Screenshots

*(Add screenshots of your application here)*

### Homepage
![Homepage Screenshot](screenshots/homepage.png)

### Product Listing
![Products Screenshot](screenshots/products.png)

### Admin Dashboard
![Admin Screenshot](screenshots/admin.png)

### Analytics
![Analytics Screenshot](screenshots/analytics.png)

---

**Made with Python & Flask** 🐍 ⚡
