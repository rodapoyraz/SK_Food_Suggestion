from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import requests
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'your_secret_key'
API_KEY = 'a35c67528fe34873ba1f903dd1809b78'
API_URL = 'https://api.spoonacular.com/recipes/complexSearch'

USER_DATABASE = {
    "ilovekebab": "1234"
}

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS preferences (
        user_id INTEGER,
        country TEXT,
        meal_type TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS favorites (
        user_id INTEGER,
        food_name TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        user_id INTEGER,
        note TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

def check_user(username, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(username, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
    conn.commit()
    conn.close()

def get_food_suggestions(country, meal_type):
    params = {
        'apiKey': API_KEY,
        'cuisine': country,
        'mealType': meal_type,
        'number': 5
    }
    response = requests.get(API_URL, params=params)
    return response.json().get('results', [])

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in USER_DATABASE and USER_DATABASE[username] == password:
            session['user_id'] = username
            return redirect('/main')
        user = check_user(username, password)
        if user:
            session['user_id'] = user[0]
            return redirect('/main')
        return 'Invalid login, try again.'
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        create_user(username, password)
        return redirect('/login')
    return render_template('signup.html')

@app.route('/main')
def main_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('main.html')

@app.route('/kebabs')
def kebabs():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('kebabs.html')

@app.route('/suggestions', methods=['GET', 'POST'])
def suggestions():
    if 'user_id' not in session:
        return redirect('/login')
    if request.method == 'POST':
        country = request.form['country']
        meal_type = request.form['meal_type']
        foods = get_food_suggestions(country, meal_type)
        return render_template('suggestions.html', foods=foods)
    return render_template('suggestions.html')

@app.route('/favorites')
def favorites():
    if 'user_id' not in session:
        return redirect('/login')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT food_name FROM favorites WHERE user_id=?', (session['user_id'],))
    foods = cursor.fetchall()
    conn.close()
    return render_template('favorites.html', foods=foods)

@app.route('/add_favorite', methods=['POST'])
def add_favorite():
    if 'user_id' not in session:
        return redirect('/login')
    food_name = request.form['food_name']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO favorites (user_id, food_name) VALUES (?, ?)', (session['user_id'], food_name))
    conn.commit()
    conn.close()
    return redirect('/favorites')

@app.route('/notes')
def notes():
    if 'user_id' not in session:
        return redirect('/login')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT note FROM notes WHERE user_id=?', (session['user_id'],))
    notes = cursor.fetchall()
    conn.close()
    return render_template('notes.html', notes=notes)

@app.route('/add_note', methods=['POST'])
def add_note():
    if 'user_id' not in session:
        return redirect('/login')
    note = request.form['note']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO notes (user_id, note) VALUES (?, ?)', (session['user_id'], note))
    conn.commit()
    conn.close()
    return redirect('/notes')

@app.route('/delete_note', methods=['POST'])
def delete_note():
    if 'user_id' not in session:
        return redirect('/login')
    note = request.form['note']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM notes WHERE user_id=? AND note=?', (session['user_id'], note))
    conn.commit()
    conn.close()
    return redirect('/notes')

@app.route('/download_pdf/<food_name>')
def download_pdf(food_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', size=12)
    pdf.cell(200, 10, txt=f"Recipe for {food_name}", ln=True)
    pdf.output(f"{food_name}.pdf")
    return redirect('/kebabs')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
