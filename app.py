from flask import Flask, render_template, request, redirect, session, flash
from passlib.hash import sha256_crypt
import mysql.connector as mariadb
import re

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

mariadb_connection = mariadb.connect(user='user', password='password', database='Login')

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

    if user and sha256_crypt.verify(password, user[1]):
        session['logged_in'] = True
        session['role'] = user[3]  # Get user role from database
        session['name'] = user[5]
        session['balance'] = user[4]
        print(session['name'])
        session['username']=user[0] # Get username from database
        return redirect('/dashboard')
    else:
        flash('Invalid username or password')
        return redirect('/')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name=request.form['name']
        username = request.form['username']
        password = request.form['password']
        grade = request.form['grade']
        email = request.form['email']
        role = request.form['role']

        cur = mariadb_connection.cursor(buffered=True)
        # Check if the username already exists
        cur.execute('SELECT * FROM Login WHERE username=%s', (username,))
        existing_user = cur.fetchone()
        if existing_user:
            flash('Username already exists!')
            return redirect('/register')

        # Encrypt the password
        hashed_password = sha256_crypt.encrypt(password)
        #cur.execute('INSERT INTO UserBalance (username, balance) VALUES (%s, %s)',(username, 10))
        # Insert new user into the database
        cur.execute('INSERT INTO Login (name, username, password, email, role, balance, grade) VALUES (%s, %s, %s, %s, %s, %s, %s)', (name, username, hashed_password, email, role, 0, grade))
        mariadb_connection.commit()
        cur.close()

        redirect('/')
        flash('Registration successful! Please log in.')


    return render_template('register.html')





@app.route('/dashboard')
def dashboard():
    cur = mariadb_connection.cursor(buffered=True)
    if not session.get('logged_in'):
        return redirect('/')
    elif session.get('role') == 'teacher':
        return render_template('teacher_dashboard.html')
    elif session.get('role') == 'student':
        return render_template('student_dashboard.html')
    else:
        # Handle other roles or situations
        return redirect('/')

@app.route('/transfer_money', methods=['POST'])
def transfer_money():
    if not session.get('logged_in') or session.get('role') != 'teacher':
        flash('You need to be logged in to transfer money.')
        return redirect('/')

    recipient = request.form['recipient']
    amount = int(request.form['amount'])
    print(amount)

    # Retrieve current user's balance
    cur = mariadb_connection.cursor(buffered=True)
    cur.execute('SELECT balance FROM Login WHERE username = %s', (session['username'],))
    current_balance = int(str(cur.fetchone()[0]))
    print(current_balance)
    
    # Check if the recipient exists
    cur.execute('SELECT * FROM Login WHERE username = %s', (recipient,))
    recipient_data = cur.fetchone()

    if not recipient_data:
        flash('Recipient does not exist.')
        return redirect('/dashboard')


    # Update recipient's balance
    cur.execute('SELECT balance FROM Login WHERE username = %s', (recipient,))
    recipient_balance = int(str(cur.fetchone()[0]))
    new_balance_recipient = recipient_balance + int(amount)
    cur.execute('UPDATE Login SET balance = %s WHERE username = %s', (new_balance_recipient, recipient))


    # Record the transaction
    cur.execute('INSERT INTO transaction_history (sender, recipient, amount) VALUES (%s, %s, %s)', (session['username'], recipient, amount))

    mariadb_connection.commit()
    cur.close()

    flash(f'Successfully Awarded {amount} points to {recipient}.')
    return redirect('/dashboard')


@app.route('/deduct', methods=['POST'])
def deduct_money():
    if not session.get('logged_in') or session.get('role') != 'teacher':
        flash('You need to be logged in to transfer money.')
        return redirect('/')

    recipient = request.form['recipient']
    amount = int(request.form['amount'])
    amount2 = amount
    amount -= amount*2
    print(amount)

    # Retrieve current user's balance
    cur = mariadb_connection.cursor(buffered=True)
    cur.execute('SELECT balance FROM Login WHERE username = %s', (session['username'],))
    current_balance = int(str(cur.fetchone()[0]))
    print(current_balance)

    # Check if the recipient exists
    cur.execute('SELECT * FROM Login WHERE username = %s', (recipient,))
    recipient_data = cur.fetchone()

    if not recipient_data:
        flash('Recipient does not exist.')
        return redirect('/dashboard')

    # Update recipient's balance
    cur.execute('SELECT balance FROM Login WHERE username = %s', (recipient,))
    recipient_balance = int(str(cur.fetchone()[0]))
    new_balance_recipient = recipient_balance + int(amount)
    cur.execute('UPDATE Login SET balance = %s WHERE username = %s', (new_balance_recipient, recipient))

    # Record the transaction
    cur.execute('INSERT INTO transaction_history (sender, recipient, amount) VALUES (%s, %s, %s)',
                (session['username'], recipient, amount))

    mariadb_connection.commit()
    cur.close()

    flash(f'Successfully deducted {amount2} points from {recipient}.')
    return redirect('/dashboard')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='5000')

