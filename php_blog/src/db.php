<?php
// src/db.php

$db_file = __DIR__ . '/blog.sqlite';

try {
    $pdo = new PDO("sqlite:$db_file");
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    die("Database connection failed: " . $e->getMessage());
}

// Helper function to get all articles
function get_articles() {
    global $pdo;
    $stmt = $pdo->query("SELECT * FROM articles ORDER BY created_at DESC");
    return $stmt->fetchAll(PDO::FETCH_ASSOC);
}

// Helper function to get a single article
function get_article($id) {
    global $pdo;
    // VULNERABILITY: Intentionally not checking if ID is valid integer here, 
    // though prepared statements prevent SQLi, we might use ID elsewhere for XSS.
    $stmt = $pdo->prepare("SELECT * FROM articles WHERE id = :id");
    $stmt->execute([':id' => $id]);
    return $stmt->fetch(PDO::FETCH_ASSOC);
}

// Helper function to get comments for an article
function get_comments($article_id) {
    global $pdo;
    $stmt = $pdo->prepare("SELECT * FROM comments WHERE article_id = :article_id ORDER BY created_at ASC");
    $stmt->execute([':article_id' => $article_id]);
    return $stmt->fetchAll(PDO::FETCH_ASSOC);
}

// Helper function to add a comment
function add_comment($article_id, $author, $content) {
    global $pdo;
    // VULNERABILITY: Stored XSS potential here - we are just inserting. 
    // The vulnerability happens when DISPLAYING this data.
    $stmt = $pdo->prepare("INSERT INTO comments (article_id, author, content, created_at) VALUES (:article_id, :author, :content, datetime('now'))");
    $stmt->execute([
        ':article_id' => $article_id,
        ':author' => $author,
        ':content' => $content
    ]);
}
?>
