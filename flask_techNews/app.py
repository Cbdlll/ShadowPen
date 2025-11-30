from flask import Flask, render_template, request, redirect, url_for, g, flash, make_response
import sqlite3
from db import get_db_connection, init_db
import os

app = Flask(__name__)
app.secret_key = 'super_secret_vulnerable_key'

# Initialize DB on start if not exists
if not os.path.exists('tech_news.db'):
    init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    # Vulnerability 10: Tag Filtering (Reflected)
    # Vulnerability 7: JS Context Injection (Category)
    tag = request.args.get('tag', '')
    category = request.args.get('category', 'All')
    
    query = "SELECT * FROM articles"
    params = []
    if category != 'All':
        query += " WHERE category = ?"
        params.append(category)
    
    articles = conn.execute(query, params).fetchall()
    conn.close()
    
    # Pass raw tag and category to template for XSS
    return render_template('index.html', articles=articles, tag=tag, category=category)

@app.route('/search')
def search():
    # Vulnerability 1: Search Bar (Reflected)
    query = request.args.get('q', '')
    conn = get_db_connection()
    articles = conn.execute("SELECT * FROM articles WHERE title LIKE ?", ('%' + query + '%',)).fetchall()
    conn.close()
    return render_template('search.html', query=query, articles=articles)

@app.route('/article/<int:article_id>', methods=['GET', 'POST'])
def article(article_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        # Vulnerability 2: Article Comments (Stored)
        username = request.form.get('username', 'Anonymous')
        content = request.form.get('content', '')
        conn.execute('INSERT INTO comments (article_id, username, content) VALUES (?, ?, ?)', 
                     (article_id, username, content))
        conn.commit()
        return redirect(url_for('article', article_id=article_id))
    
    article = conn.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()
    comments = conn.execute('SELECT * FROM comments WHERE article_id = ? ORDER BY created_at DESC', (article_id,)).fetchall()
    conn.close()
    
    if article is None:
        return render_template('404.html', path=request.path), 404
        
    # Vulnerability 9: Image Credit (Stored) - article.credit is passed
    return render_template('article.html', article=article, comments=comments)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # Vulnerability 3: User Bio (Stored)
    # Simulating a logged-in user 'admin' for demo purposes
    conn = get_db_connection()
    if request.method == 'POST':
        bio = request.form.get('bio', '')
        website = request.form.get('website', '')
        conn.execute("UPDATE users SET bio = ?, website = ? WHERE username = 'admin'", (bio, website))
        conn.commit()
        flash('Profile updated!')
        return redirect(url_for('profile'))
    
    user = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/login')
def login():
    # Vulnerability 6: Login Redirect (Reflected/Attribute)
    next_url = request.args.get('next', '')
    return render_template('login.html', next=next_url)

@app.route('/subscribe')
def subscribe():
    # Vulnerability 5: Newsletter (DOM-based) - Handled in template/JS
    return render_template('subscribe.html')

@app.route('/admin')
def admin():
    # Vulnerability 8: User-Agent (Reflected/Stored simulation)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    return render_template('admin.html', user_agent=user_agent)

@app.errorhandler(404)
def page_not_found(e):
    # Vulnerability 4: URL Path (Reflected)
    return render_template('404.html', path=request.path), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
