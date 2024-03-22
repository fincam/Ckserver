from flask import Flask, render_template, request, redirect, session, flash
from passlib.hash import sha256_crypt
import mysql.connector as mariadb

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

mariadb_connection = mariadb.connect(user='chooseAUserName', password='chooseAPassword', database='Login')

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    login = request.form
    username = login['username']
    password = login['password']

    cur = mariadb_connection.cursor(buffered=True)
    cur.execute('SELECT * FROM Login WHERE username=%s', (username,))
    user = cur.fetchone()

    if user and sha256_crypt.verify(password, user[2]):
        session['logged_in'] = True
        session['role'] = user[4]  # Get user role from database
        session['user_id'] = user[0] # Get user_id from database
        session['username']=user[1] # Get username from database
        return redirect('/dashboard')
    else:
        flash('Invalid username or password')
        return redirect('/')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        # Check for duplicate username in the database
        cur = mariadb_connection.cursor(buffered=True)
        cur.execute('SELECT * FROM Login WHERE username=%s', (username,))
        existing_user = cur.fetchone()
        if existing_user:
            flash('Username already exists!')
            return redirect('/register')
        
        # Validate password format
        if not validate_password(password):
            flash('Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character, and be at least 8 characters long.')
            return redirect('/register')
        
        # Encrypt the password
        hashed_password = sha256_crypt.encrypt(password)
        
        # Insert new user into the Login table
        cur.execute('INSERT INTO Login (username, password, email) VALUES (%s, %s, %s)', (username, hashed_password, email))
        mariadb_connection.commit()
        
        # Retrieve the uid of the newly inserted user
        cur.execute('SELECT uid FROM Login WHERE username=%s', (username,))
        uid = cur.fetchone()[0]
        
        # Insert the new user into the UserBalance table
        cur.execute('INSERT INTO UserBalance (uid, username) VALUES (%s, %s)', (uid, username))
        mariadb_connection.commit()
        #
        cur.close()
        
        flash('Registration successful! Please log in.')
        return redirect('/')
    
    return render_template('register.html')



        # Encrypt the password
        hashed_password = sha256_crypt.encrypt(password)
        cur.execute('INSERT INTO UserBalance (username, balance) VALUES (%s, %s)',(username, 10))
        # Insert new user into the database
        cur.execute('INSERT INTO Login (username, password, email, role) VALUES (%s, %s, %s, %s)', (username, hashed_password, email, role))
        mariadb_connection.commit()
        cur.close()
        
        flash('Registration successful! Please log in.')
        return redirect('/')

    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    cur = mariadb_connection.cursor(buffered=True)
    if not session.get('logged_in'):
        return redirect('/')
    elif session.get('role') == 'student':
        return render_template('student_dashboard.html')
    elif session.get('role') == 'teacher':
        return render_template('teacher_dashboard.html')
    else:
        # Handle other roles or situations
        return redirect('/')

@app.route('/transfer_money', methods=['POST'])
def transfer_money():
    if not session.get('logged_in'):
        flash('You need to be logged in to transfer money.')
        return redirect('/')

    recipient = request.form['recipient']
    amount = int(request.form['amount'])

    # Retrieve current user's balance
    cur = mariadb_connection.cursor(buffered=True)
    cur.execute('SELECT balance FROM transaction WHERE username = %s', (session['username'],))
    current_balance = int(str(cur.fetchone()[0]))

    # Check if the recipient exists
    cur.execute('SELECT * FROM transaction WHERE username = %s', (recipient,))
    recipient_data = cur.fetchone()

    if not recipient_data:
        flash('Recipient does not exist.')
        return redirect('/dashboard')

    # Check if the user has sufficient balance to transfer
    if amount > current_balance:
        flash('Insufficient balance to transfer.')
        return redirect('/dashboard')

    # Update sender's balance
    new_balance_sender = current_balance - int(amount)
    cur.execute('UPDATE transaction SET balance = %s WHERE username = %s', (new_balance_sender, session['username']))

    # Update recipient's balance
    cur.execute('SELECT balance FROM transaction WHERE username = %s', (recipient,))
    recipient_balance = int(str(cur.fetchone()[0]))
    new_balance_recipient = recipient_balance + int(amount)
    cur.execute('UPDATE transaction SET balance = %s WHERE username = %s', (new_balance_recipient, recipient))

    # Record the transaction
    cur.execute('INSERT INTO transaction_history (sender, recipient, amount) VALUES (%s, %s, %s)', (session['username'], recipient, amount))

    mariadb_connection.commit()
    cur.close()

    flash(f'Successfully transferred {amount} to {recipient}.')
    return redirect('/dashboard')



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='5000')
