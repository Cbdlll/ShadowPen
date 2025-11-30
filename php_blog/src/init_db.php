<?php
// src/init_db.php
require_once 'db.php';

try {
    // Create Articles Table
    $pdo->exec("CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        author TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )");

    // Create Comments Table
    $pdo->exec("CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER NOT NULL,
        author TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(article_id) REFERENCES articles(id)
    )");

    // Check if data exists
    $stmt = $pdo->query("SELECT COUNT(*) FROM articles");
    if ($stmt->fetchColumn() == 0) {
        // Seed Articles
        $articles = [
            [
                'title' => 'Welcome to My Secure Blog',
                'content' => 'This is the first post on my new secure blog platform. I built it from scratch using PHP and SQLite. Feel free to leave a comment!',
                'author' => 'Admin'
            ],
            [
                'title' => 'The Future of Web Security',
                'content' => 'Web security is evolving. We need to be vigilant about XSS, SQL Injection, and other threats. Always sanitize your inputs!',
                'author' => 'SecurityExpert'
            ],
            [
                'title' => 'Why I Love PHP',
                'content' => 'PHP is a great language for web development. It is fast, flexible, and easy to learn. Plus, it powers a huge portion of the web.',
                'author' => 'DevJohn'
            ]
        ];

        $insert = $pdo->prepare("INSERT INTO articles (title, content, author) VALUES (:title, :content, :author)");
        foreach ($articles as $article) {
            $insert->execute($article);
        }

        // Seed Comments
        $comments = [
            [
                'article_id' => 1,
                'author' => 'Alice',
                'content' => 'Great post! Looking forward to more.'
            ],
            [
                'article_id' => 1,
                'author' => 'Bob',
                'content' => 'Nice design. Very clean.'
            ]
        ];

        $insert_comment = $pdo->prepare("INSERT INTO comments (article_id, author, content) VALUES (:article_id, :author, :content)");
        foreach ($comments as $comment) {
            $insert_comment->execute($comment);
        }
        
        // echo "Database initialized and seeded successfully.";
    } else {
        // echo "Database already initialized.";
    }

} catch (PDOException $e) {
    die("Initialization failed: " . $e->getMessage());
}
?>
