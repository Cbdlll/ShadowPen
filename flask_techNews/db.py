import sqlite3
import os

DB_PATH = 'tech_news.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            bio TEXT DEFAULT '',
            website TEXT DEFAULT ''
        )
    ''')
    
    # Articles table
    cursor.execute('''
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT NOT NULL,
            image_url TEXT,
            credit TEXT DEFAULT '',
            category TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Comments table
    cursor.execute('''
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles (id)
        )
    ''')
    
    # Seed data
    cursor.execute("INSERT INTO users (username, password, bio) VALUES ('admin', 'admin123', '<b>System Administrator</b>')")
    cursor.execute("INSERT INTO users (username, password, bio) VALUES ('alice', 'password', 'Tech enthusiast')")
    
    articles = [
        ('The Future of AI in 2025', 'Artificial Intelligence is evolving rapidly...', 'John Doe', 'https://picsum.photos/800/400?random=1', 'Photo by <b>Unsplash</b>', 'AI'),
        ('New Quantum Processor Unveiled', 'Researchers have demonstrated a new 500-qubit processor...', 'Jane Smith', 'https://picsum.photos/800/400?random=2', 'Source: TechDaily', 'Hardware'),
        ('SpaceX Launches Starship', 'The massive rocket achieved orbit for the first time...', 'Elon Fan', 'https://picsum.photos/800/400?random=3', 'Credit: SpaceX', 'Space'),
        ('Python 4.0 Rumors', 'Community discusses potential features for the next major version...', 'Guido', 'https://picsum.photos/800/400?random=4', 'Community', 'Programming')
    ]
    
    cursor.executemany('INSERT INTO articles (title, content, author, image_url, credit, category) VALUES (?, ?, ?, ?, ?, ?)', articles)
    
    cursor.execute("INSERT INTO comments (article_id, username, content) VALUES (1, 'alice', 'Great article! <script>console.log(1)</script>')")
    
    conn.commit()
    conn.close()
    print("Database initialized.")

if __name__ == '__main__':
    init_db()
