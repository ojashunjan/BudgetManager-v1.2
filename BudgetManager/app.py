import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for Flask
import matplotlib.pyplot as plt
import io
from datetime import datetime

app = Flask(__name__)
DB_NAME = 'budget.db'

# Initialize DB if it doesn't exist
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                description TEXT,
                date TEXT NOT NULL
            )
        ''')
        conn.commit()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/', methods=['GET'])
def index():
    category_filter = request.args.get('category')
    date_filter = request.args.get('date')

    conn = get_db_connection()
    query = "SELECT * FROM transactions WHERE 1=1"
    params = []

    if category_filter and category_filter != 'All':
        query += " AND category = ?"
        params.append(category_filter)

    if date_filter:
        query += " AND date = ?"
        params.append(date_filter)

    query += " ORDER BY date DESC"

    transactions = conn.execute(query, params).fetchall()

    income = conn.execute("SELECT SUM(amount) FROM transactions WHERE type='income'").fetchone()[0] or 0
    expense = conn.execute("SELECT SUM(amount) FROM transactions WHERE type='expense'").fetchone()[0] or 0
    balance = income - expense

    categories = conn.execute("SELECT DISTINCT category FROM transactions").fetchall()
    categories_list = ['All'] + [row['category'] for row in categories]

    conn.close()

    return render_template('index.html', transactions=transactions, balance=balance, categories=categories_list, selected_category=category_filter or 'All', selected_date=date_filter or '')

@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
        except ValueError:
            amount = 0.0
        category = request.form['category']
        t_type = request.form['type']
        description = request.form['description']
        date = request.form['date']

        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            date = datetime.today().strftime('%Y-%m-%d')

        conn = get_db_connection()
        conn.execute('INSERT INTO transactions (amount, category, type, description, date) VALUES (?, ?, ?, ?, ?)',
                     (amount, category, t_type, description, date))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    categories = ['Food', 'Rent', 'Salary', 'Entertainment', 'Utilities', 'Other']

    return render_template('add.html', categories=categories)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_transaction(id):
    conn = get_db_connection()
    transaction = conn.execute('SELECT * FROM transactions WHERE id = ?', (id,)).fetchone()

    if transaction is None:
        conn.close()
        return "Transaction not found", 404

    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
        except ValueError:
            amount = 0.0
        category = request.form['category']
        t_type = request.form['type']
        description = request.form['description']
        date = request.form['date']

        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            date = datetime.today().strftime('%Y-%m-%d')

        conn.execute('''
            UPDATE transactions
            SET amount = ?, category = ?, type = ?, description = ?, date = ?
            WHERE id = ?
        ''', (amount, category, t_type, description, date, id))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    categories = ['Food', 'Rent', 'Salary', 'Entertainment', 'Utilities', 'Other']
    conn.close()
    return render_template('edit.html', transaction=transaction, categories=categories)

@app.route("/spending_chart")
def spending_chart():
    conn = get_db_connection()
    rows = conn.execute("SELECT category, SUM(amount) AS total FROM transactions WHERE type = 'expense' GROUP BY category").fetchall()
    conn.close()

    labels = [row["category"] for row in rows]
    values = [round(row["total"], 2) for row in rows]
    return jsonify(labels=labels, values=values)

if __name__ == '__main__':
    app.run(debug=True)

###updated 2025-06-29