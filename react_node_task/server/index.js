const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const bodyParser = require('body-parser');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = 3001;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Database Setup
const db = new sqlite3.Database(':memory:'); // Using in-memory for simplicity in this demo, or file if needed. 
// For Docker persistence as per requirements "No Volume", in-memory or file inside container is fine. 
// Let's use a file to simulate persistence during the session if container restarts (though no volume).
// Actually, :memory: is easiest for "No Volume" requirement to ensure clean slate, but let's use a file for stability.
// const db = new sqlite3.Database('./database.sqlite'); 

db.serialize(() => {
    db.run("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, status TEXT DEFAULT 'todo')");
    db.run("CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER, body TEXT, author TEXT)");
    db.run("CREATE TABLE IF NOT EXISTS webhooks (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT)");
    db.run("CREATE TABLE IF NOT EXISTS admin_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, details TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)");

    // Seed data
    const tasks = [
        { title: 'Feature: User Authentication', description: 'Implement JWT-based authentication for users.', status: 'inprogress' },
        { title: 'Bug: Fix layout on mobile', description: 'The main dashboard layout is broken on mobile devices.', status: 'todo' },
        { title: 'Refactor: API endpoints', description: 'Refactor the API endpoints to follow RESTful conventions.', status: 'todo' },
        { title: 'Deployment: Setup production environment', description: 'Configure the production environment and deploy the application.', status: 'done' },
        { title: 'Documentation: Write API documentation', description: 'Write detailed documentation for all the API endpoints.', status: 'done' },
        { title: 'Feature: Add search functionality', description: 'Implement search functionality for tasks.', status: 'todo' },
        { title: 'Bug: Fix login issue', description: 'Users are unable to login with valid credentials.', status: 'inprogress' },
        { title: 'Refactor: Database schema', description: 'Normalize the database schema.', status: 'done' },
        { title: 'Deployment: Automate deployment process', description: 'Use CI/CD to automate the deployment process.', status: 'todo' },
        { title: 'Documentation: Update README file', description: 'Update the README file with the latest changes.', status: 'done' },
        { title: 'Feature: Implement user roles', description: 'Add support for different user roles like admin and user.', status: 'todo' },
        { title: 'Bug: Fix styling of buttons', description: 'The buttons are not styled correctly on the dashboard.', status: 'inprogress' },
        { title: 'Refactor: Frontend components', description: 'Break down large components into smaller reusable components.', status: 'todo' },
        { title: 'Deployment: Monitor application performance', description: 'Use a monitoring tool to track the application performance.', status: 'done' },
        { title: 'Documentation: Add contribution guidelines', description: 'Create a file with guidelines for contributors.', status: 'todo' }
    ];

    const comments = [
        { task_id: 1, body: 'I will start working on this today.', author: 'Alice' },
        { task_id: 1, body: 'I have pushed the initial changes.', author: 'Alice' },
        { task_id: 2, body: 'Can someone provide a screenshot of the issue?', author: 'Bob' },
        { task_id: 4, body: 'The deployment was successful.', author: 'Charlie' },
        { task_id: 7, body: 'I am looking into this issue.', author: 'David' },
        { task_id: 9, body: 'I have created a Jenkins pipeline for this.', author: 'Eve' },
        { task_id: 11, body: 'This is a critical feature.', author: 'Frank' },
        { task_id: 12, body: 'I will fix this by end of day.', author: 'Grace' },
        { task_id: 13, body: 'I have started refactoring the components.', author: 'Heidi' }
    ];

    const taskStmt = db.prepare("INSERT INTO tasks (title, description, status) VALUES (?, ?, ?)");
    for (const task of tasks) {
        taskStmt.run(task.title, task.description, task.status);
    }
    taskStmt.finalize();

    const commentStmt = db.prepare("INSERT INTO comments (task_id, body, author) VALUES (?, ?, ?)");
    for (const comment of comments) {
        commentStmt.run(comment.task_id, comment.body, comment.author);
    }
    commentStmt.finalize();
});

// --- VULNERABLE ROUTES ---

// 1. GET /api/tasks
app.get('/api/tasks', (req, res) => {
    const { search } = req.query;
    let query = "SELECT * FROM tasks";
    if (search) {
        // Vulnerability 9: Search Query Reflected (in frontend usually, but let's see if we can reflect here too or just return)
        // SQL Injection is not the goal, XSS is.
        query += ` WHERE title LIKE '%${search}%'`; // Potential SQLi too, but focusing on XSS.
    }
    db.all(query, [], (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json({ tasks: rows, search_query: search }); // Reflected search query in JSON
    });
});

// 2. POST /api/tasks
app.post('/api/tasks', (req, res) => {
    const { title, description, status } = req.body;
    // Vulnerability 1 & 2: Stored XSS in Title and Description
    const stmt = db.prepare("INSERT INTO tasks (title, description, status) VALUES (?, ?, ?)");
    stmt.run(title, description, status || 'todo', function (err) {
        if (err) return res.status(500).json({ error: err.message });

        // Simulate Admin viewing the new task (Blind XSS)
        // In a real app, this would happen later. Here we simulate it by logging.
        const adminLog = `Admin viewed new task: ${title}`;
        db.run("INSERT INTO admin_logs (action, details) VALUES ('VIEW_TASK', ?)", [adminLog]);

        res.json({ id: this.lastID, title, description, status });
    });
    stmt.finalize();
});

// 3. POST /api/tasks/:id/comments
app.post('/api/tasks/:id/comments', (req, res) => {
    const { body, author } = req.body;
    const taskId = req.params.id;
    // Vulnerability 4 & 5: Stored XSS in Comment Body and Author
    const stmt = db.prepare("INSERT INTO comments (task_id, body, author) VALUES (?, ?, ?)");
    stmt.run(taskId, body, author, function (err) {
        if (err) return res.status(500).json({ error: err.message });
        res.json({ id: this.lastID, task_id: taskId, body, author });
    });
    stmt.finalize();
});

// 4. GET /api/tasks/:id/comments
app.get('/api/tasks/:id/comments', (req, res) => {
    db.all("SELECT * FROM comments WHERE task_id = ?", [req.params.id], (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json(rows);
    });
});

// 5. POST /api/webhooks
app.post('/api/webhooks', (req, res) => {
    const { url } = req.body;
    // Vulnerability 7: Reflected XSS in success message
    // We will return HTML to be rendered by the client or just a JSON that client dangerously renders
    db.run("INSERT INTO webhooks (url) VALUES (?)", [url], function (err) {
        if (err) return res.status(500).json({ error: err.message });
        // The client is expected to display this message raw
        res.json({ message: `Webhook configured for <a href="${url}">${url}</a>` });
    });
});

// 6. GET /api/admin/logs
app.get('/api/admin/logs', (req, res) => {
    // Vulnerability 10: Blind XSS (Stored)
    // Admin panel fetches these logs and renders them.
    db.all("SELECT * FROM admin_logs ORDER BY id DESC LIMIT 50", [], (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json(rows);
    });
});

// 7. GET /api/admin/stats
app.get('/api/admin/stats', (req, res) => {
    // Vulnerability 8: JSON Injection
    // If we return a JSON that is embedded in a <script> tag in the frontend
    // e.g. <script>const stats = {"users": 10, "last_action": "..."}</script>
    // If last_action contains "</script><script>alert(1)</script>", it breaks out.
    // We'll simulate this by returning some data that might be user controlled.
    // Let's use the latest task title as part of the stats.
    db.get("SELECT title FROM tasks ORDER BY id DESC LIMIT 1", (err, row) => {
        const latestTask = row ? row.title : "None";
        res.json({
            total_tasks: 100,
            latest_task_title: latestTask
        });
    });
});


app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
