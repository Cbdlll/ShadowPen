<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TechInsights Blog</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding-top: 60px; }
        .footer { margin-top: 50px; padding: 20px 0; background-color: #f8f9fa; border-top: 1px solid #e9ecef; }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
    <div class="container">
        <a class="navbar-brand" href="index.php">TechInsights</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav me-auto">
                <li class="nav-item"><a class="nav-link" href="index.php">Home</a></li>
                <li class="nav-item"><a class="nav-link" href="contact.php">Contact</a></li>
                <li class="nav-item"><a class="nav-link" href="admin.php">Admin</a></li>
                <li class="nav-item"><a class="nav-link" href="profile.php">Profile</a></li>
                <li class="nav-item"><a class="nav-link" href="debug.php">Debug Info</a></li>
            </ul>
            <form class="d-flex" action="search.php" method="GET">
                <input class="form-control me-2" type="search" name="q" placeholder="Search" aria-label="Search">
                <button class="btn btn-outline-light" type="submit">Search</button>
            </form>
            <div class="navbar-text ms-3 text-white">
                <?php
                // VULNERABILITY #1: Reflected XSS via Cookie
                // If the 'username' cookie is set, it is echoed back without sanitization.
                if (isset($_COOKIE['username'])) {
                    echo "Hello, " . $_COOKIE['username']; 
                } else {
                    echo '<a href="admin.php" class="text-decoration-none text-white">Login</a>';
                }
                ?>
            </div>
        </div>
    </div>
</nav>

<div class="container mt-4">
