const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const bodyParser = require('body-parser');
const path = require('path');
const marked = require('marked');

const app = express();
const port = 3000;

// Middleware
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));
app.use(bodyParser.urlencoded({ extended: true }));

// Database Setup (In-memory for non-persistence)
const db = new sqlite3.Database(':memory:');

db.serialize(() => {
    db.run(`CREATE TABLE feedbacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    author TEXT,
    tags TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);

    db.run(`CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    bio TEXT
  )`);

    // Seed Data
    const stmt = db.prepare("INSERT INTO feedbacks (title, description, author, tags) VALUES (?, ?, ?, ?)");
    stmt.run("Great tool!", "I really like the **interface**. It's very clean.", "Alice", "ui,ux");
    stmt.run("Feature Request: Dark Mode", "A dark mode option would be amazing for my eyes at night!", "Bob", "feature,ui");
    stmt.run("Minor Typo on Homepage", "Found a small typo in the welcome message.", "Charlie", "bug,copy");
    stmt.run("How do I export my data?", "Is there a way to export my feedback data? I can't seem to find it.", "Diana", "help,question");
    stmt.run("Excellent Customer Support", "The support team was incredibly helpful and resolved my issue within minutes.", "Eve", "praise,support");
    stmt.finalize();

    db.run("INSERT INTO users (username, bio) VALUES ('admin', 'System Administrator')");
});

// Helper to mock a logged-in user
const currentUser = {
    username: 'Guest',
    bio: 'Just a guest user.'
};

// Routes

// 1. Home Page - Lists feedbacks
app.get('/', (req, res) => {
    db.all("SELECT * FROM feedbacks ORDER BY created_at DESC", (err, rows) => {
        if (err) {
            return res.status(500).send(err.message);
        }
        // Vulnerability 4: Tags are stored and will be rendered unsafely in the view
        res.render('index', { feedbacks: rows });
    });
});

// 2. Detail Page - Shows feedback details
app.get('/feedback/:id', (req, res) => {
    const id = req.params.id;
    // Vulnerability 6: Return URL reflected in "Back" link
    const returnUrl = req.query.returnUrl || '/';

    db.get("SELECT * FROM feedbacks WHERE id = ?", [id], (err, row) => {
        if (err) {
            return res.status(500).send(err.message);
        }
        if (!row) {
            // Vulnerability 7: Error message reflected
            return res.render('error', { error: `Feedback with ID ${id} not found.` });
        }

        // Vulnerability 2: Unsafe Markdown parsing
        // We manually implement a "vulnerable" markdown parser or just use marked without sanitization
        // marked is safe by default in newer versions unless we specifically allow html? 
        // Actually marked < 0.7.0 was vulnerable, but here we can just use EJS <%- %> for the description
        // and maybe a custom "parser" that doesn't escape HTML.
        // Let's just say we use marked but we will output it with <%- %> in EJS.
        // And we won't use marked's sanitizer if it exists.

        // Actually, let's just pass the raw description and let the view handle the unsafe rendering via <%- %>
        // But the requirement says "Markdown parsing vulnerability".
        // Let's simulate a "custom" markdown parser that is just a pass-through for HTML
        const htmlDescription = marked.parse(row.description, { mangle: false, headerIds: false });

        res.render('detail', {
            feedback: row,
            description: htmlDescription,
            returnUrl: returnUrl
        });
    });
});

// 3. Submit Page
app.get('/submit', (req, res) => {
    res.render('submit');
});

// 4. Handle Submission
app.post('/submit', (req, res) => {
    const { title, description, author, tags } = req.body;
    // Vulnerability 1, 3, 4: Stored XSS in title, author, tags
    const stmt = db.prepare("INSERT INTO feedbacks (title, description, author, tags) VALUES (?, ?, ?, ?)");
    stmt.run(title, description, author, tags, function (err) {
        if (err) {
            return res.send(err.message);
        }
        res.redirect('/');
    });
});

// 5. Search Page
app.get('/search', (req, res) => {
    const query = req.query.q || '';
    // Vulnerability 5: Search query reflected
    db.all("SELECT * FROM feedbacks WHERE title LIKE ? OR description LIKE ?", [`%${query}%`, `%${query}%`], (err, rows) => {
        if (err) {
            return res.status(500).send(err.message);
        }
        res.render('search', { feedbacks: rows, query: query });
    });
});

// 6. User Profile
app.get('/user', (req, res) => {
    // Vulnerability 8: User bio stored XSS
    // In a real app, we'd update the bio. Here we just show the static one or update it via a hidden endpoint.
    // Let's allow updating bio via query param for demonstration if needed, or just use the seeded one.
    // Let's add a POST to update bio.

    db.get("SELECT * FROM users WHERE username = 'admin'", (err, row) => {
        res.render('user', { user: row });
    });
});

app.post('/user/update', (req, res) => {
    const { bio } = req.body;
    db.run("UPDATE users SET bio = ? WHERE username = 'admin'", [bio], (err) => {
        res.redirect('/user');
    });
});

// 7. JSON Debug Endpoint
app.get('/api/debug', (req, res) => {
    const data = req.query.data;
    // Vulnerability 9: JSON Reflection
    // If the browser treats this as HTML (e.g. if content-type is not set strictly or via IE sniffing), it can execute XSS.
    // Or if we explicitly send HTML content type for a JSON endpoint (common mistake).
    res.set('Content-Type', 'text/html'); // Force HTML interpretation for demonstration
    res.send(`{"debug": true, "data": "${data}"}`);
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
