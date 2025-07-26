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
from decimal import Decimal, getcontext # Import getcontext for precision control

# Set the precision for Decimal calculations
getcontext().prec = 10 # Set precision to 10 decimal places for financial calculations

app = Flask(__name__)
app.secret_key = 'stocker_secret_key_2024'

# AWS Configuration
AWS_REGION = 'us-east-1'
USERS_TABLE = 'stocker_user'
STOCKS_TABLE = 'stocker_stocks'
TRANSACTIONS_TABLE = 'stocker_transactions'
PORTFOLIO_TABLE = 'stocker_portfolio'
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:971422691207:StockerUserAccountTopic' # Replace with your actual SNS Topic ARN

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
            print(f"Table {USERS_TABLE} already exists.")
        except boto3.client('dynamodb').exceptions.ResourceNotFoundException:
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
            users_table.wait_until_exists() # Wait for table to be active
            print(f"Table {USERS_TABLE} is active.")
        
        # Create Stocks table
        try:
            stocks_table.load()
            print(f"Table {STOCKS_TABLE} already exists.")
        except boto3.client('dynamodb').exceptions.ResourceNotFoundException:
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
            stocks_table.wait_until_exists()
            print(f"Table {STOCKS_TABLE} is active.")
        
        # Create Transactions table
        try:
            transactions_table.load()
            print(f"Table {TRANSACTIONS_TABLE} already exists.")
        except boto3.client('dynamodb').exceptions.ResourceNotFoundException:
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
            transactions_table.wait_until_exists()
            print(f"Table {TRANSACTIONS_TABLE} is active.")
        
        # Create Portfolio table
        try:
            portfolio_table.load()
            print(f"Table {PORTFOLIO_TABLE} already exists.")
        except boto3.client('dynamodb').exceptions.ResourceNotFoundException:
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
            portfolio_table.wait_until_exists()
            print(f"Table {PORTFOLIO_TABLE} is active.")
        
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
    """Generates initial stock prices and stores them in DynamoDB."""
    for symbol in STOCK_SYMBOLS:
        # Convert random float to Decimal for precision
        base_price = Decimal(str(random.uniform(50, 500))).quantize(Decimal('0.01')) 
        stock_prices[symbol] = base_price

        # Update DynamoDB stocks table
        try:
            stocks_table.put_item(
                Item={
                    'symbol': symbol,
                    'current_price': base_price,
                    'last_updated': datetime.now().isoformat()
                }
            )
        except Exception as e:
            print(f"Error updating stock price in DynamoDB: {e}")

def update_stock_prices():
    """Continuously updates stock prices and stores them in DynamoDB."""
    while True:
        for symbol in STOCK_SYMBOLS:
            # Generate a random change and convert to Decimal
            change = Decimal(str(random.uniform(-0.05, 0.05))) 
            new_price = stock_prices[symbol] * (1 + change)
            new_price = new_price.quantize(Decimal('0.01')) # Round to 2 decimal places

            stock_prices[symbol] = new_price

            # Update DynamoDB
            try:
                stocks_table.put_item(
                    Item={
                        'symbol': symbol,
                        'current_price': new_price,
                        'last_updated': datetime.now().isoformat()
                    }
                )
            except Exception as e:
                print(f"Error updating stock price in DynamoDB: {e}")

        time.sleep(10)

# Initialize stock prices
generate_stock_prices()

# Start price update thread
price_thread = threading.Thread(target=update_stock_prices, daemon=True)
price_thread.start()

def hash_password(password):
    """Hashes the given password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def send_sns_message(subject, message, email=None):
    """Sends an SNS message to the specified topic or email."""
    try:
        if email:
            # Note: For actual email delivery via SNS, you'd typically need to subscribe the email
            # to the SNS topic first, or use direct publish with a 'TargetArn' for an endpoint.
            # This example assumes the topic is configured to deliver to emails.
            print(f"Simulating SNS email to {email}: Subject='{subject}', Message='{message}'")
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=message,
                Subject=subject
            )
        else:
            print(f"Simulating SNS topic publish: Subject='{subject}', Message='{message}'")
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=message,
                Subject=subject
            )
    except Exception as e:
        print(f"Error sending SNS message: {e}")

@app.route('/')
def index():
    """Renders the home page."""
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles user registration."""
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
    """Checks if a username already exists (for AJAX validation)."""
    username = request.args.get('username')
    try:
        # Scan for username (since it's not the primary key, this can be inefficient for large tables)
        response = users_table.scan(
            FilterExpression=Key('username').eq(username)
        )
        exists = len(response['Items']) > 0
        return jsonify({'exists': exists})
    except Exception as e:
        print(f"Error checking username: {e}")
        return jsonify({'exists': False})

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
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
    """Logs out the current user."""
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """Renders the trader dashboard."""
    if 'user_email' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    try:
        # Get user's portfolio
        response = portfolio_table.query(
            KeyConditionExpression=Key('user_id').eq(session['user_email'])
        )
        portfolio = response['Items']
        
        return render_template('dashboard.html', stocks=stock_prices, portfolio=portfolio)
    except Exception as e:
        print(f"Error fetching portfolio for dashboard: {e}")
        flash(f"Error loading dashboard: {e}", 'error')
        return render_template('dashboard.html', stocks=stock_prices, portfolio=[])

@app.route('/trade', methods=['GET', 'POST'])
def trade():
    """Handles stock buy/sell operations."""
    if 'user_email' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        stock_symbol = request.form['stock_symbol'].upper() # Ensure symbol is uppercase
        try:
            quantity = Decimal(request.form['quantity']) # Convert quantity to Decimal
        except ValueError:
            flash('Invalid quantity. Please enter a number.', 'error')
            return redirect(url_for('trade'))

        trade_type = request.form['trade_type']
        
        if stock_symbol not in stock_prices:
            flash('Invalid stock symbol!', 'error')
            return redirect(url_for('trade'))
            
        price = stock_prices[stock_symbol] # This is already a Decimal
        
        try:
            # Record trade
            trade_id = str(uuid.uuid4())
            transactions_table.put_item(
                Item={
                    'id': trade_id,
                    'user_id': session['user_email'],
                    'stock_symbol': stock_symbol,
                    'qty': quantity, # Storing Decimal
                    'price': price, # Storing Decimal
                    'type': trade_type,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            # Update portfolio
            # Fetch existing portfolio item
            response = portfolio_table.get_item(
                Key={'user_id': session['user_email'], 'stock_symbol': stock_symbol}
            )
            existing_portfolio_item = response.get('Item')

            if trade_type == 'BUY':
                if existing_portfolio_item:
                    # Convert existing quantity and avg_price to Decimal for calculation
                    existing_qty = Decimal(str(existing_portfolio_item['quantity']))
                    existing_avg_price = Decimal(str(existing_portfolio_item['avg_price']))
                    
                    new_qty = existing_qty + quantity
                    # Calculate new average price using Decimal
                    new_avg = ((existing_qty * existing_avg_price) + (quantity * price)) / new_qty
                    new_avg = new_avg.quantize(Decimal('0.01')) # Round to 2 decimal places
                    
                    portfolio_table.put_item(
                        Item={
                            'user_id': session['user_email'],
                            'stock_symbol': stock_symbol,
                            'quantity': new_qty, # Storing Decimal
                            'avg_price': new_avg, # Storing Decimal
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                else:
                    portfolio_table.put_item(
                        Item={
                            'user_id': session['user_email'],
                            'stock_symbol': stock_symbol,
                            'quantity': quantity, # Storing Decimal
                            'avg_price': price, # Storing Decimal
                            'timestamp': datetime.now().isoformat()
                        }
                    )
            
            elif trade_type == 'SELL':
                if existing_portfolio_item:
                    existing_qty = Decimal(str(existing_portfolio_item['quantity']))
                    existing_avg_price = Decimal(str(existing_portfolio_item['avg_price']))

                    if quantity > existing_qty:
                        flash(f'You only own {existing_qty} shares of {stock_symbol}. Cannot sell more than you own.', 'error')
                        # Delete the transaction if the sell quantity exceeds owned quantity
                        transactions_table.delete_item(Key={'id': trade_id})
                        return redirect(url_for('trade'))
                        
                    new_qty = existing_qty - quantity
                    
                    if new_qty <= 0:
                        portfolio_table.delete_item(
                            Key={'user_id': session['user_email'], 'stock_symbol': stock_symbol}
                        )
                    else:
                        portfolio_table.put_item(
                            Item={
                                'user_id': session['user_email'],
                                'stock_symbol': stock_symbol,
                                'quantity': new_qty, # Storing Decimal
                                'avg_price': existing_avg_price, # Avg price doesn't change on sell
                                'timestamp': datetime.now().isoformat()
                            }
                        )
                else:
                    flash(f'You do not own any shares of {stock_symbol} to sell.', 'error')
                    # Delete the transaction if trying to sell non-existent stock
                    transactions_table.delete_item(Key={'id': trade_id})
                    return redirect(url_for('trade'))
            
            # Send trade notification via SNS
            send_sns_message(
                'Trade Confirmation',
                f'Your {trade_type} order for {quantity} shares of {stock_symbol} at ${price.quantize(Decimal("0.01"))} has been executed.',
                session['user_email']
            )
            
            flash(f'{trade_type} order completed successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Trade error: {str(e)}', 'error')
    
    return render_template('trade.html', stocks=stock_prices)

@app.route('/portfolio')
def portfolio():
    """Renders the user's portfolio."""
    if 'user_email' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    try:
        response = portfolio_table.query(
            KeyConditionExpression=Key('user_id').eq(session['user_email'])
        )
        portfolio = response['Items']
        # Convert Decimal values in portfolio items to string for JSON serialization if needed,
        # or handle them directly in the template. DynamoDB returns Decimals.
        return render_template('portfolio.html', portfolio=portfolio, current_prices=stock_prices)
    except Exception as e:
        print(f"Error fetching portfolio: {e}")
        flash(f"Error loading portfolio: {e}", 'error')
        return render_template('portfolio.html', portfolio=[], current_prices=stock_prices)

@app.route('/history')
def history():
    """Renders the user's transaction history."""
    if 'user_email' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    try:
        response = transactions_table.query(
            IndexName='user_id-index', # Use the GSI for efficient querying by user_id
            KeyConditionExpression=Key('user_id').eq(session['user_email'])
        )
        trades = sorted(response['Items'], key=lambda x: x['timestamp'], reverse=True)
        return render_template('history.html', trades=trades)
    except Exception as e:
        print(f"Error fetching transaction history: {e}")
        flash(f"Error loading history: {e}", 'error')
        return render_template('history.html', trades=[])

@app.route('/help', methods=['GET', 'POST'])
def help():
    """Handles help requests."""
    if request.method == 'POST':
        # Ensure user is logged in to associate help request
        if 'user_email' not in session:
            flash('Please log in to send a help request.', 'error')
            return redirect(url_for('login'))

        message = request.form.get('message', '')
        if not message.strip():
            flash('Message cannot be empty.', 'error')
            return redirect(url_for('help'))

        send_sns_message(
            'Help Request from Stocker',
            f'User {session.get("username", "Unknown")} ({session.get("user_email", "N/A")}) sent: {message}'
        )
        flash('Your message was sent!', 'success')
        return redirect(url_for('help'))
        
    return render_template('help.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    """Renders the admin dashboard with overall statistics."""
    if 'user_email' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    try:
        # Get statistics
        users_response = users_table.scan()
        total_traders = len([u for u in users_response['Items'] if u.get('role') == 'Trader'])
        
        trades_response = transactions_table.scan()
        total_trades = len(trades_response['Items'])
        
        portfolio_response = portfolio_table.scan()
        # Ensure Decimal conversion for sum calculation
        total_market_value = sum([Decimal(str(p.get('quantity', 0))) * Decimal(str(p.get('avg_price', 0))) for p in portfolio_response['Items']])
        total_market_value = total_market_value.quantize(Decimal('0.01')) # Round for display
        
        return render_template('admin_dashboard.html', 
                               total_traders=total_traders,
                               total_trades=total_trades,
                               total_market_value=total_market_value)
    except Exception as e:
        print(f"Error fetching admin dashboard data: {e}")
        flash(f"Error loading admin dashboard: {e}", 'error')
        return render_template('admin_dashboard.html', 
                               total_traders=0,
                               total_trades=0,
                               total_market_value=Decimal('0.00'))

@app.route('/admin_portfolio')
def admin_portfolio():
    """Renders the overall portfolio view for admins."""
    if 'user_email' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    try:
        portfolios = portfolio_table.scan()['Items']
        return render_template('admin_portfolio.html', portfolios=portfolios, current_prices=stock_prices)
    except Exception as e:
        print(f"Error fetching admin portfolio: {e}")
        flash(f"Error loading admin portfolio: {e}", 'error')
        return render_template('admin_portfolio.html', portfolios=[])

@app.route('/admin_history')
def admin_history():
    """Renders the overall transaction history for admins."""
    if 'user_email' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    try:
        trades = transactions_table.scan()['Items']
        trades = sorted(trades, key=lambda x: x['timestamp'], reverse=True)
        return render_template('admin_history.html', trades=trades)
    except Exception as e:
        print(f"Error fetching admin history: {e}")
        flash(f"Error loading admin history: {e}", 'error')
        return render_template('admin_history.html', trades=[])

@app.route('/admin_manage')
def admin_manage():
    """Allows admins to manage users and view their portfolio values."""
    if 'user_email' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    try:
        users_response = users_table.scan()
        traders = [u for u in users_response['Items'] if u.get('role') == 'Trader']
        
        # Get portfolio values for each trader
        portfolio_response = portfolio_table.scan()
        portfolio_by_user = {}
        for p in portfolio_response['Items']:
            user_id = p['user_id']
            # Ensure Decimal conversion for calculations
            quantity = Decimal(str(p.get('quantity', 0)))
            avg_price = Decimal(str(p.get('avg_price', 0)))

            if user_id not in portfolio_by_user:
                portfolio_by_user[user_id] = {'value': Decimal('0.00'), 'stocks': 0}
            portfolio_by_user[user_id]['value'] += quantity * avg_price
            portfolio_by_user[user_id]['stocks'] += 1
        
        # Combine data
        for trader in traders:
            email = trader['email']
            if email in portfolio_by_user:
                trader['portfolio_value'] = portfolio_by_user[email]['value'].quantize(Decimal('0.01'))
                trader['stocks_owned'] = portfolio_by_user[email]['stocks']
            else:
                trader['portfolio_value'] = Decimal('0.00')
                trader['stocks_owned'] = 0
        
        traders = sorted(traders, key=lambda x: x.get('created_at', ''), reverse=True)
        return render_template('admin_manage.html', traders=traders)
    except Exception as e:
        print(f"Error fetching admin manage data: {e}")
        flash(f"Error loading admin manage page: {e}", 'error')
        return render_template('admin_manage.html', traders=[])

@app.route('/api/stock_prices')
def api_stock_prices():
    """API endpoint to get current stock prices."""
    # Convert Decimal values to string for JSON serialization
    # jsonify handles Decimal by default in recent Flask versions, but explicit conversion
    # can prevent issues with older versions or specific environments.
    # For this case, it's fine as stock_prices already holds Decimal objects.
    return jsonify({s: str(p) for s, p in stock_prices.items()})

def open_browser():
    """Opens the web browser to the application URL."""
    time.sleep(1.5)
    try:
        webbrowser.open('http://localhost:5000')
    except Exception as e:
        print(f"Could not open browser: {e}")

if __name__ == '__main__':
    # Create DynamoDB tables if they don't exist
    create_dynamodb_tables()
    
    # Open browser automatically only once - prevent multiple windows
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
    app.run(debug=True, host='0.0.0.0', port=5000)
