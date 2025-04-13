from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import csv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import random



app = Flask(__name__)
app.secret_key = '______'

# Database connection configuration
db = mysql.connector.connect(
    host="_______",
    user="_____",
    password="______",
    database="ecommerce"
)

cursor = db.cursor()

# Create users table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL,
        password VARCHAR(255) NOT NULL
    )
""")
def read_products(file_path):
    products = []
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        products = list(reader)
    return products


def content_based_recommendations(df, selected_product):
    item_name = selected_product['product_name']

    # Check if the item name exists in the data
    if item_name not in df['product_name'].values:
        print(f"Item '{item_name}' not found in our data.")
        return pd.DataFrame()

    # Create a TF-IDF vectorizer for item descriptions
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')

    # Apply TF-IDF vectorization to item descriptions
    tfidf_matrix_content = tfidf_vectorizer.fit_transform(df['Tags'])

    # Calculate cosine similarity between items based on descriptions
    cosine_similarities_content = cosine_similarity(tfidf_matrix_content, tfidf_matrix_content)

    # Find the index of the item
    item_index = df[df['product_name'] == item_name].index[0]

    # Get the cosine similarity scores for the item
    similar_items = list(enumerate(cosine_similarities_content[item_index]))

    # Sort similar items by similarity score in descending order
    similar_items = sorted(similar_items, key=lambda x: x[1], reverse=True)

    # Get the top 10 most similar items (excluding the item itself)
    top_similar_items = similar_items[1:11]

    # Get the indices of the top similar items
    recommended_item_indices = [x[0] for x in top_similar_items]

    # Get the details of the top similar items
    recommended_items_details = df.iloc[recommended_item_indices][
        ['product_name', 'rating', 'rating_count', 'actual_price','discounted_price', 'category', 'about_product', 'review_content',
         'img_link', 'product_id']]

    return recommended_items_details

@app.route('/')
def index():

    return render_template('index.html')  # Main page

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT id, password FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]  # Store user ID in session
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials. Please try again.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                       (username, email, password))
        db.commit()

        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/home')
def home():
    products = read_products(r'C:\Users\LENOVO\Downloads\trending_products.csv')
    return render_template('home.html',products=products)  # Home page after login


@app.route('/product/<product_id>')
def product_details(product_id):
    productss = read_products(r'C:\Users\LENOVO\Downloads\productss.csv')

    # Correct filtering logic
    selected_product = next((product for product in productss if product['product_id'] == product_id), None)

    if selected_product is None:
        flash("Product not found", "danger")
        return redirect(url_for('home'))

    df=pd.DataFrame(productss)

    recommended_items_details = content_based_recommendations(df, selected_product)
    recommended_items_details = recommended_items_details.to_dict(orient='records')

    return render_template('product_details.html', product=selected_product,recommendations=recommended_items_details)


@app.route('/category/<category_name>')
def category_products(category_name):
    # Read the products from the CSV file
    products = read_products(r'C:\Users\LENOVO\Downloads\productss.csv')

    # Filter products by category
    filtered_products = [product for product in products if product['categories'] == category_name]
    filtered_products = random.sample(filtered_products, min(len(filtered_products), 15))
    # Render the category page with the filtered products
    return render_template('category_products.html', category_name=category_name, products=filtered_products)


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        # Get the search query from the form
        query = request.form['query'].lower()

        # Read the products from the CSV file
        products = read_products(r'C:\Users\LENOVO\Downloads\productss.csv')

        # Create a DataFrame for easier manipulation
        df = pd.DataFrame(products)

        # Combine 'category' and 'product_name' for similarity calculation
        df['combined'] = df['category'] + ' ' + df['product_name']

        # Initialize TF-IDF Vectorizer
        vectorizer = TfidfVectorizer()

        # Fit and transform the combined text data
        tfidf_matrix = vectorizer.fit_transform(df['combined'])

        # Transform the query using the same vectorizer
        query_vec = vectorizer.transform([query])

        # Calculate cosine similarity between the query and all products
        cosine_similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()

        # Get the top 10 most similar products in descending order
        top_indices = cosine_similarities.argsort()[-10:][::-1]

        # Filter and sort the products based on cosine similarity
        search_results = [products[i] for i in top_indices]

        # Render the search results page with the filtered products
        return render_template('search_results.html', query=query, products=search_results)
    else:
        # If accessed via GET (e.g., by directly visiting the URL), redirect to home
        return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove the user_id from the session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(debug=True)
