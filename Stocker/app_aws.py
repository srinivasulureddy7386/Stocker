import os
import boto3
import hashlib
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import webbrowser
import threading
import time
import random
from boto3.dynamodb.conditions import Key

app = Flask(__name__)
app.secret_key = 'stocker_secret_key_2024'

# AWS Configuration
AWS_REGION = 'us-east-1'
USERS_TABLE = 'stocker_user'
STOCKS_TABLE = 'stocker_stocks'
TRANSACTIONS_TABLE = 'stocker_transactions'
PORTFOLIO_TABLE = 'stocker_portfolio'
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:xxxx:stocker_alerts'

# Initialize AWS services
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
sns_client = boto3.client('sns', region_name=AWS_REGION)

# DynamoDB tables
users_table = dynamodb.Table(USERS_TABLE)
stocks_table = dynamodb.Table(STOCKS_TABLE)
transactions_table = dynamodb.Table(TRANSACTIONS_TABLE)
portfolio_table = dynamodb.Table(PORTFOLIO_TABLE)

def create_dynamodb_tables():
    """Create DynamoDB tables if they don't exist"""
    try:
        # Create Users table
        try:
            users_table.load()
        except:
            dynamodb.create_table(
                TableName=USERS_TABLE,
                KeySchema=[
                    {'AttributeName': 'email', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'email', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print(f"Created table: {USERS_TABLE}")
        
        # Create Stocks table
        try:
            stocks_table.load()
        except:
            dynamodb.create_table(
                TableName=STOCKS_TABLE,
                KeySchema=[
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'symbol', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print(f"Created table: {STOCKS_TABLE}")
        
        # Create Transactions table
        try:
            transactions_table.load()
        except:
            dynamodb.create_table(
                TableName=TRANSACTIONS_TABLE,
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'S'},
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'user_id-index',
                        'KeySchema': [
                            {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'}
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print(f"Created table: {TRANSACTIONS_TABLE}")
        
        # Create Portfolio table
        try:
            portfolio_table.load()
        except:
            dynamodb.create_table(
                TableName=PORTFOLIO_TABLE,
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'stock_symbol', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'S'},
                    {'AttributeName': 'stock_symbol', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print(f"Created table: {PORTFOLIO_TABLE}")
        
        print("All DynamoDB tables are ready!")
        
    except Exception as e:
        print(f"Error creating DynamoDB tables: {e}")

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
        
        # Update DynamoDB stocks table
        try:
            stocks_table.put_item(
                Item={
                    'symbol': symbol,
                    'current_price': stock_prices[symbol],
                    'last_updated': datetime.now().isoformat()
                }
            )
        except Exception as e:
            print(f"Error updating stock price: {e}")

def update_stock_prices():
    while True:
        for symbol in STOCK_SYMBOLS:
            change = random.uniform(-0.05, 0.05)  # ±5% change
            stock_prices[symbol] = round(stock_prices[symbol] * (1 + change), 2)
            
            # Update DynamoDB
            try:
                stocks_table.put_item(
                    Item={
                        'symbol': symbol,
                        'current_price': stock_prices[symbol],
                        'last_updated': datetime.now().isoformat()
                    }
                )
            except Exception as e:
                print(f"Error updating stock price: {e}")
        
        time.sleep(10)

# Initialize stock prices
generate_stock_prices()

# Start price update thread
price_thread = threading.Thread(target=update_stock_prices, daemon=True)
price_thread.start()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def send_sns_message(subject, message, email=None):
    try:
        if email:
            # Send to specific email
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=message,
                Subject=subject
            )
        else:
            # Send to topic
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=message,
                Subject=subject
            )
    except Exception as e:
        print(f"Error sending SNS message: {e}")

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
        
        try:
            # Check if email exists
            response = users_table.get_item(Key={'email': email})
            if 'Item' in response:
                flash('Email already exists!', 'error')
                return render_template('signup.html')
            
            # Insert new user
            hashed_password = hash_password(password)
            users_table.put_item(
                Item={
                    'email': email,
                    'username': username,
                    'password': hashed_password,
                    'role': role,
                    'created_at': datetime.now().isoformat()
                }
            )
            
            # Send welcome email via SNS
            send_sns_message(
                'Welcome to Stocker',
                f'Thank you {username} for signing up as a {role}',
                email
            )
            
            flash('Account created successfully!', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            flash(f'Error creating account: {str(e)}', 'error')
    
    return render_template('signup.html')

@app.route('/check_username')
def check_username():
    username = request.args.get('username')
    try:
        # Scan for username (since it's not the primary key)
        response = users_table.scan(
            FilterExpression=Key('username').eq(username)
        )
        exists = len(response['Items']) > 0
        return jsonify({'exists': exists})
    except Exception as e:
        return jsonify({'exists': False})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        try:
            response = users_table.get_item(Key={'email': email})
            if 'Item' in response:
                user = response['Item']
                if user['password'] == hash_password(password) and user['role'] == role:
                    session['user_email'] = email
                    session['username'] = user['username']
                    session['role'] = user['role']
                    flash('Login successful!', 'success')
                    
                    if role == 'Admin':
                        return redirect(url_for('admin_dashboard'))
                    else:
                        return redirect(url_for('dashboard'))
                else:
                    flash('Incorrect email/password or role mismatch!', 'error')
            else:
                flash('User not found!', 'error')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    try:
        # Get user's portfolio
        response = portfolio_table.scan(
            FilterExpression=Key('user_id').eq(session['user_email'])
        )
        portfolio = response['Items']
        
        return render_template('dashboard.html', stocks=stock_prices, portfolio=portfolio)
    except Exception as e:
        return render_template('dashboard.html', stocks=stock_prices, portfolio=[])

@app.route('/trade', methods=['GET', 'POST'])
def trade():
    if 'user_email' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        stock_symbol = request.form['stock_symbol']
        quantity = int(request.form['quantity'])
        trade_type = request.form['trade_type']
        
        if stock_symbol not in stock_prices:
            flash('Invalid stock symbol!', 'error')
            return redirect(url_for('trade'))
            
        price = stock_prices[stock_symbol]
        
        try:
            # Record trade
            trade_id = str(uuid.uuid4())
            transactions_table.put_item(
                Item={
                    'id': trade_id,
                    'user_id': session['user_email'],
                    'stock_symbol': stock_symbol,
                    'qty': quantity,
                    'price': price,
                    'type': trade_type,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            # Update portfolio
            portfolio_key = f"{session['user_email']}#{stock_symbol}"
            
            if trade_type == 'BUY':
                try:
                    response = portfolio_table.get_item(
                        Key={'user_id': session['user_email'], 'stock_symbol': stock_symbol}
                    )
                    if 'Item' in response:
                        existing = response['Item']
                        new_qty = existing['quantity'] + quantity
                        new_avg = ((existing['quantity'] * existing['avg_price']) + (quantity * price)) / new_qty
                        portfolio_table.put_item(
                            Item={
                                'user_id': session['user_email'],
                                'stock_symbol': stock_symbol,
                                'quantity': new_qty,
                                'avg_price': new_avg,
                                'timestamp': datetime.now().isoformat()
                            }
                        )
                    else:
                        portfolio_table.put_item(
                            Item={
                                'user_id': session['user_email'],
                                'stock_symbol': stock_symbol,
                                'quantity': quantity,
                                'avg_price': price,
                                'timestamp': datetime.now().isoformat()
                            }
                        )
                except Exception as e:
                    print(f"Portfolio update error: {e}")
            
            elif trade_type == 'SELL':
                try:
                    response = portfolio_table.get_item(
                        Key={'user_id': session['user_email'], 'stock_symbol': stock_symbol}
                    )
                    if 'Item' in response:
                        existing = response['Item']
                        new_qty = existing['quantity'] - quantity
                        if new_qty <= 0:
                            portfolio_table.delete_item(
                                Key={'user_id': session['user_email'], 'stock_symbol': stock_symbol}
                            )
                        else:
                            portfolio_table.put_item(
                                Item={
                                    'user_id': session['user_email'],
                                    'stock_symbol': stock_symbol,
                                    'quantity': new_qty,
                                    'avg_price': existing['avg_price'],
                                    'timestamp': datetime.now().isoformat()
                                }
                            )
                    else:
                        # Create negative position (short selling)
                        portfolio_table.put_item(
                            Item={
                                'user_id': session['user_email'],
                                'stock_symbol': stock_symbol,
                                'quantity': -quantity,
                                'avg_price': price,
                                'timestamp': datetime.now().isoformat()
                            }
                        )
                except Exception as e:
                    print(f"Portfolio update error: {e}")
            
            # Send trade notification via SNS
            send_sns_message(
                'Trade Confirmation',
                f'Your {trade_type} order for {quantity} shares of {stock_symbol} at ${price} has been executed.',
                session['user_email']
            )
            
            flash(f'{trade_type} order completed successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Trade error: {str(e)}', 'error')
    
    return render_template('trade.html', stocks=stock_prices)

@app.route('/portfolio')
def portfolio():
    if 'user_email' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    try:
        response = portfolio_table.scan(
            FilterExpression=Key('user_id').eq(session['user_email'])
        )
        portfolio = response['Items']
        return render_template('portfolio.html', portfolio=portfolio, current_prices=stock_prices)
    except Exception as e:
        return render_template('portfolio.html', portfolio=[], current_prices=stock_prices)

@app.route('/history')
def history():
    if 'user_email' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    try:
        response = transactions_table.scan(
            FilterExpression=Key('user_id').eq(session['user_email'])
        )
        trades = sorted(response['Items'], key=lambda x: x['timestamp'], reverse=True)
        return render_template('history.html', trades=trades)
    except Exception as e:
        return render_template('history.html', trades=[])

@app.route('/help', methods=['GET', 'POST'])
def help():
    if request.method == 'POST':
        # Send help request via SNS
        message = request.form.get('message', '')
        send_sns_message(
            'Help Request from Stocker',
            f'User {session.get("username", "Unknown")} sent: {message}'
        )
        flash('Your message was sent!', 'success')
        return redirect(url_for('help'))
    
    return render_template('help.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_email' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    try:
        # Get statistics
        users_response = users_table.scan()
        total_traders = len([u for u in users_response['Items'] if u['role'] == 'Trader'])
        
        trades_response = transactions_table.scan()
        total_trades = len(trades_response['Items'])
        
        portfolio_response = portfolio_table.scan()
        total_market_value = sum([p['quantity'] * p['avg_price'] for p in portfolio_response['Items']])
        
        return render_template('admin_dashboard.html', 
                             total_traders=total_traders,
                             total_trades=total_trades,
                             total_market_value=total_market_value)
    except Exception as e:
        return render_template('admin_dashboard.html', 
                             total_traders=0,
                             total_trades=0,
                             total_market_value=0)

@app.route('/admin_portfolio')
def admin_portfolio():
    if 'user_email' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    try:
        portfolios = portfolio_table.scan()['Items']
        return render_template('admin_portfolio.html', portfolios=portfolios)
    except Exception as e:
        return render_template('admin_portfolio.html', portfolios=[])

@app.route('/admin_history')
def admin_history():
    if 'user_email' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    try:
        trades = transactions_table.scan()['Items']
        trades = sorted(trades, key=lambda x: x['timestamp'], reverse=True)
        return render_template('admin_history.html', trades=trades)
    except Exception as e:
        return render_template('admin_history.html', trades=[])

@app.route('/admin_manage')
def admin_manage():
    if 'user_email' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    try:
        users_response = users_table.scan()
        traders = [u for u in users_response['Items'] if u['role'] == 'Trader']
        
        # Get portfolio values for each trader
        portfolio_response = portfolio_table.scan()
        portfolio_by_user = {}
        for p in portfolio_response['Items']:
            user_id = p['user_id']
            if user_id not in portfolio_by_user:
                portfolio_by_user[user_id] = {'value': 0, 'stocks': 0}
            portfolio_by_user[user_id]['value'] += p['quantity'] * p['avg_price']
            portfolio_by_user[user_id]['stocks'] += 1
        
        # Combine data
        for trader in traders:
            email = trader['email']
            if email in portfolio_by_user:
                trader['portfolio_value'] = portfolio_by_user[email]['value']
                trader['stocks_owned'] = portfolio_by_user[email]['stocks']
            else:
                trader['portfolio_value'] = 0
                trader['stocks_owned'] = 0
        
        traders = sorted(traders, key=lambda x: x['created_at'], reverse=True)
        return render_template('admin_manage.html', traders=traders)
    except Exception as e:
        return render_template('admin_manage.html', traders=[])

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
    # Create DynamoDB tables if they don't exist
    create_dynamodb_tables()
    
    # Open browser automatically only once - prevent multiple windows
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
    app.run(debug=True, port=5000)