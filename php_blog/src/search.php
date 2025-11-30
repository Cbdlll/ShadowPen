<?php
require_once 'db.php';
include 'header.php';

$query = isset($_GET['q']) ? $_GET['q'] : '';
?>

<div class="row">
    <div class="col-md-12">
        <h1 class="mb-4">Search Results</h1>
        
        <div class="alert alert-info">
            <!-- VULNERABILITY #4: Reflected XSS via Search Query -->
            <!-- The search query is echoed back directly. -->
            You searched for: <strong><?php echo $query; ?></strong>
        </div>

        <?php
        if ($query) {
            // Safe SQL search (using prepared statements in db.php if we implemented search logic there, 
            // but for simplicity here we just show a placeholder or empty results as the vuln is the echo above).
            // Let's just list all articles for now to keep it simple, or filter in PHP.
            $all_articles = get_articles();
            $found = false;
            foreach ($all_articles as $article) {
                if (stripos($article['title'], $query) !== false || stripos($article['content'], $query) !== false) {
                    $found = true;
                    ?>
                    <div class="card mb-3">
                        <div class="card-body">
                            <h3 class="card-title"><a href="article.php?id=<?php echo $article['id']; ?>"><?php echo htmlspecialchars($article['title']); ?></a></h3>
                            <p class="card-text"><?php echo substr(htmlspecialchars($article['content']), 0, 100); ?>...</p>
                        </div>
                    </div>
                    <?php
                }
            }
            if (!$found) {
                echo "<p>No results found.</p>";
            }
        }
        ?>
    </div>
</div>

<?php include 'footer.php'; ?>
