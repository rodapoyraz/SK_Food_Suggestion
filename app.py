from flask import Flask, request, render_template, redirect, url_for, session
import sqlite3
import requests
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'your_secret_key'
API_KEY = 'a35c67528fe34873ba1f903dd1809b78'
API_URL = 'https://api.spoonacular.com/recipes/complexSearch'


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


def get_food_suggestions(country=None, meal_type=None, diet=None, ingredients=None, query=None):
    params = {
        'apiKey': API_KEY,
        'number': 10  # Increase results
    }

    if country:
        params['cuisine'] = country
    if meal_type:
        params['type'] = meal_type
    if diet:
        params['diet'] = diet
    if ingredients:
        params['includeIngredients'] = ingredients
    if query:
        params['query'] = query

    response = requests.get(API_URL, params=params)
    results = response.json().get('results', [])

    # Simplify the results
    recipes = [
        {
            'id': recipe.get('id'),
            'title': recipe.get('title', 'No Title'),
            'image': recipe.get('image', ''),
        }
        for recipe in results
    ]
    return recipes


@app.route('/')
def login():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login_user():
    username = request.form['username']
    password = request.form['password']
    user = check_user(username, password)
    if user:
        session['user_id'] = user[0]
        return redirect('/main')
    return 'Invalid login, try again.'


@app.route('/signup')
def signup():
    return render_template('signup.html')


@app.route('/signup', methods=['POST'])
def signup_user():
    username = request.form['username']
    password = request.form['password']
    create_user(username, password)
    return redirect('/')


@app.route('/main')
def main_page():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('main.html')


@app.route('/kebabs')
def kebabs():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('kebabs.html')


@app.route('/suggestions', methods=['GET', 'POST'])
def suggestions():
    if 'user_id' not in session:
        return redirect('/')

    if request.method == 'POST':
        country = request.form.get('country')
        meal_type = request.form.get('meal_type')
        diet = request.form.get('diet')
        ingredients = request.form.get('ingredients')
        query = request.form.get('query')

        recipes = get_food_suggestions(country, meal_type, diet, ingredients, query)
        return render_template('suggestions.html', recipes=recipes)

    return render_template('suggestions.html', recipes=[])


@app.route('/recipe/<int:recipe_id>')
def recipe_details(recipe_id):
    if 'user_id' not in session:
        return redirect('/')

    # Fetch recipe details from Spoonacular
    response = requests.get(
        f"https://api.spoonacular.com/recipes/{recipe_id}/information",
        params={'apiKey': API_KEY}
    )
    recipe = response.json()

    # Handle case where no recipe is found
    if not recipe:
        return "Recipe details not available.", 404

    # Render the recipe details page
    return render_template('recipe_details.html', recipe=recipe)


@app.route('/favorites')
def favorites():
    if 'user_id' not in session:
        return redirect('/')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT food_name FROM favorites WHERE user_id=?', (session['user_id'],))
    foods = cursor.fetchall()
    conn.close()
    return render_template('favorites.html', foods=foods)


@app.route('/add_favorite', methods=['POST'])
def add_favorite():
    if 'user_id' not in session:
        return redirect('/')
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
        return redirect('/')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT note FROM notes WHERE user_id=?', (session['user_id'],))
    notes = cursor.fetchall()
    conn.close()
    return render_template('notes.html', notes=notes)


@app.route('/add_note', methods=['POST'])
def add_note():
    if 'user_id' not in session:
        return redirect('/')
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
        return redirect('/')
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
    return redirect('/')


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
