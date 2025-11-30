<?php
require_once 'db.php';
// Initialize DB if needed (auto-run once)
require_once 'init_db.php';

include 'header.php';
?>

<div class="row">
    <div class="col-md-8">
        <h1 class="mb-4">Latest Articles</h1>
        
        <?php
        $articles = get_articles();
        foreach ($articles as $article):
        ?>
            <div class="card mb-4 shadow-sm">
                <div class="card-body">
                    <h2 class="card-title"><a href="article.php?id=<?php echo $article['id']; ?>" class="text-dark text-decoration-none"><?php echo htmlspecialchars($article['title']); ?></a></h2>
                    <p class="card-text text-muted">By <?php echo htmlspecialchars($article['author']); ?> on <?php echo $article['created_at']; ?></p>
                    <p class="card-text"><?php echo substr(htmlspecialchars($article['content']), 0, 150); ?>...</p>
                    <a href="article.php?id=<?php echo $article['id']; ?>" class="btn btn-primary">Read More &rarr;</a>
                </div>
            </div>
        <?php endforeach; ?>
    </div>

    <div class="col-md-4">
        <div class="card mb-4">
            <div class="card-header">About Us</div>
            <div class="card-body">
                <p>TechInsights is your go-to source for the latest in technology and security news.</p>
            </div>
        </div>

        <div class="card mb-4">
            <div class="card-header">System Info</div>
            <div class="card-body">
                <p class="small text-muted">
                    <!-- VULNERABILITY #3: Reflected XSS via User-Agent -->
                    <!-- The User-Agent string is echoed back directly. -->
                    Your Browser: <?php echo $_SERVER['HTTP_USER_AGENT']; ?>
                </p>
            </div>
        </div>
    </div>
</div>

<?php include 'footer.php'; ?>
