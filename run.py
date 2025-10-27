#!/usr/bin/env python3
"""
Simple startup script for the Textile Store Flask application
"""

import os
import sys
import subprocess

def check_requirements():
    """Check if required packages are installed"""
    try:
        import flask
        import werkzeug
        print("[OK] Flask and dependencies are installed")
        return True
    except ImportError as e:
        print(f"[ERROR] Missing dependencies: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def main():
    """Main function to start the application"""
    print("=" * 50)
    print("Textile Store - Flask E-commerce Application")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("Error: app.py not found. Please run this script from the project directory.")
        sys.exit(1)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    print("\nStarting the application...")
    print("The application will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Start the Flask application
        subprocess.run([sys.executable, 'app.py'])
    except KeyboardInterrupt:
        print("\n\nApplication stopped by user.")
    except Exception as e:
        print(f"\nError starting application: {e}")

if __name__ == "__main__":
    main()


