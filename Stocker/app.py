import os
import sqlite3
import hashlib
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import webbrowser
import threading
import time
import random

app = Flask(__name__)
app.secret_key = 'stocker_secret_key_2024'

# Initialize database
def init_db():
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Portfolio table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stock_symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            avg_price REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Trades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stock_symbol TEXT NOT NULL,
            qty INTEGER NOT NULL,
            price REAL NOT NULL,
            type TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Stock data simulation
STOCK_SYMBOLS = [
    'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 
    'ADBE', 'CRM', 'ORCL', 'INTC', 'AMD', 'PYPL', 'UBER', 'SPOT',
    'TWTR', 'SNAP', 'SQ', 'ZOOM', 'SHOP', 'ROKU', 'PINS', 'DOCU'
]

stock_prices = {}

def generate_stock_prices():
    for symbol in STOCK_SYMBOLS:
        base_price = random.uniform(50, 500)
        stock_prices[symbol] = round(base_price, 2)

def update_stock_prices():
    while True:
        for symbol in STOCK_SYMBOLS:
            change = random.uniform(-0.05, 0.05)  # ±5% change
            stock_prices[symbol] = round(stock_prices[symbol] * (1 + change), 2)
        time.sleep(10)

# Initialize stock prices
generate_stock_prices()

# Start price update thread
price_thread = threading.Thread(target=update_stock_prices, daemon=True)
price_thread.start()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        conn = sqlite3.connect('stocker.db')
        cursor = conn.cursor()
        
        # Check if username or email exists
        cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email))
        if cursor.fetchone():
            flash('Username or email already exists!', 'error')
            conn.close()
            return render_template('signup.html')
        
        # Insert new user
        hashed_password = hash_password(password)
        cursor.execute('INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)',
                      (username, email, hashed_password, role))
        conn.commit()
        conn.close()
        
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/check_username')
def check_username():
    username = request.args.get('username')
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    exists = cursor.fetchone() is not None
    conn.close()
    return jsonify({'exists': exists})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        conn = sqlite3.connect('stocker.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ? AND password = ? AND role = ?',
                      (email, hash_password(password), role))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[4]
            flash('Login successful!', 'success')
            
            if role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Incorrect email/password or role mismatch!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    # Get user's portfolio
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT stock_symbol, quantity, avg_price 
        FROM portfolio 
        WHERE user_id = ?
    ''', (session['user_id'],))
    portfolio = cursor.fetchall()
    conn.close()
    
    return render_template('dashboard.html', stocks=stock_prices, portfolio=portfolio)

@app.route('/trade', methods=['GET', 'POST'])
def trade():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        stock_symbol = request.form['stock_symbol']
        quantity = int(request.form['quantity'])
        trade_type = request.form['trade_type']
        
        if stock_symbol not in stock_prices:
            flash('Invalid stock symbol!', 'error')
            return redirect(url_for('trade'))
            
        price = stock_prices[stock_symbol]
        
        conn = sqlite3.connect('stocker.db')
        cursor = conn.cursor()
        
        # Record trade
        cursor.execute('''
            INSERT INTO trades (user_id, stock_symbol, qty, price, type)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['user_id'], stock_symbol, quantity, price, trade_type))
        
        # Update portfolio
        if trade_type == 'BUY':
            cursor.execute('''
                SELECT quantity, avg_price FROM portfolio 
                WHERE user_id = ? AND stock_symbol = ?
            ''', (session['user_id'], stock_symbol))
            existing = cursor.fetchone()
            
            if existing:
                new_qty = existing[0] + quantity
                new_avg = ((existing[0] * existing[1]) + (quantity * price)) / new_qty
                cursor.execute('''
                    UPDATE portfolio SET quantity = ?, avg_price = ?
                    WHERE user_id = ? AND stock_symbol = ?
                ''', (new_qty, new_avg, session['user_id'], stock_symbol))
            else:
                cursor.execute('''
                    INSERT INTO portfolio (user_id, stock_symbol, quantity, avg_price)
                    VALUES (?, ?, ?, ?)
                ''', (session['user_id'], stock_symbol, quantity, price))
        
        elif trade_type == 'SELL':
            cursor.execute('''
                SELECT quantity FROM portfolio 
                WHERE user_id = ? AND stock_symbol = ?
            ''', (session['user_id'], stock_symbol))
            existing = cursor.fetchone()
            
            if existing:
                new_qty = existing[0] - quantity
                if new_qty <= 0:
                    cursor.execute('''
                        DELETE FROM portfolio 
                        WHERE user_id = ? AND stock_symbol = ?
                    ''', (session['user_id'], stock_symbol))
                else:
                    cursor.execute('''
                        UPDATE portfolio SET quantity = ?
                        WHERE user_id = ? AND stock_symbol = ?
                    ''', (new_qty, session['user_id'], stock_symbol))
            else:
                # Create negative position (short selling)
                cursor.execute('''
                    INSERT INTO portfolio (user_id, stock_symbol, quantity, avg_price)
                    VALUES (?, ?, ?, ?)
                ''', (session['user_id'], stock_symbol, -quantity, price))
        
        conn.commit()
        conn.close()
        
        flash(f'{trade_type} order completed successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('trade.html', stocks=stock_prices)

@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT stock_symbol, quantity, avg_price 
        FROM portfolio 
        WHERE user_id = ?
    ''', (session['user_id'],))
    portfolio = cursor.fetchall()
    conn.close()
    
    return render_template('portfolio.html', portfolio=portfolio, current_prices=stock_prices)

@app.route('/history')
def history():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT stock_symbol, qty, price, type, timestamp 
        FROM trades 
        WHERE user_id = ? 
        ORDER BY timestamp DESC
    ''', (session['user_id'],))
    trades = cursor.fetchall()
    conn.close()
    
    return render_template('history.html', trades=trades)

@app.route('/help', methods=['GET', 'POST'])
def help():
    if request.method == 'POST':
        flash('Your message was sent!', 'success')
        return redirect(url_for('help'))
    
    return render_template('help.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'Trader'")
    total_traders = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM trades")
    total_trades = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT SUM(p.quantity * p.avg_price) 
        FROM portfolio p
    ''')
    total_market_value = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         total_traders=total_traders,
                         total_trades=total_trades,
                         total_market_value=total_market_value)

@app.route('/admin_portfolio')
def admin_portfolio():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.username, p.stock_symbol, p.quantity, p.avg_price
        FROM portfolio p
        JOIN users u ON p.user_id = u.id
        ORDER BY u.username
    ''')
    portfolios = cursor.fetchall()
    conn.close()
    
    return render_template('admin_portfolio.html', portfolios=portfolios)

@app.route('/admin_history')
def admin_history():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.username, t.stock_symbol, t.qty, t.price, t.type, t.timestamp
        FROM trades t
        JOIN users u ON t.user_id = u.id
        ORDER BY t.timestamp DESC
    ''')
    trades = cursor.fetchall()
    conn.close()
    
    return render_template('admin_history.html', trades=trades)

@app.route('/admin_manage')
def admin_manage():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.username, u.email, u.created_at,
               COALESCE(SUM(p.quantity * p.avg_price), 0) as portfolio_value,
               COUNT(p.stock_symbol) as stocks_owned
        FROM users u
        LEFT JOIN portfolio p ON u.id = p.user_id
        WHERE u.role = 'Trader'
        GROUP BY u.id, u.username, u.email, u.created_at
        ORDER BY u.created_at DESC
    ''')
    traders = cursor.fetchall()
    conn.close()
    
    return render_template('admin_manage.html', traders=traders)

@app.route('/api/stock_prices')
def api_stock_prices():
    return jsonify(stock_prices)

def open_browser():
    time.sleep(1.5)
    try:
        webbrowser.open('http://localhost:5000')
    except:
        pass

if __name__ == '__main__':
    init_db()
    # Open browser automatically only once - prevent multiple windows
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
    app.run(debug=True, port=5000)