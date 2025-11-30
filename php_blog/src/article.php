<?php
require_once 'db.php';

// Handle Comment Submission
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['comment'])) {
    $author = isset($_POST['author']) ? $_POST['author'] : 'Anonymous';
    $content = $_POST['comment'];
    $article_id = $_POST['article_id'];
    
    add_comment($article_id, $author, $content);
    // Redirect to avoid resubmission
    header("Location: article.php?id=$article_id");
    exit;
}

include 'header.php';

$id = isset($_GET['id']) ? $_GET['id'] : null;
$article = null;

if ($id) {
    $article = get_article($id);
}

if (!$article) {
    // VULNERABILITY #6: Reflected XSS via Error Message
    // The ID is echoed back in the error message.
    echo "<div class='alert alert-danger'>Error: Article with ID " . $id . " not found.</div>";
    include 'footer.php';
    exit;
}
?>

<div class="row">
    <div class="col-lg-8">
        <article>
            <h1 class="fw-bolder mb-1"><?php echo htmlspecialchars($article['title']); ?></h1>
            <div class="text-muted fst-italic mb-2">Posted on <?php echo $article['created_at']; ?> by <?php echo htmlspecialchars($article['author']); ?></div>
            <section class="mb-5">
                <p class="fs-5 mb-4"><?php echo nl2br(htmlspecialchars($article['content'])); ?></p>
            </section>
        </article>

        <section class="mb-5">
            <div class="card bg-light">
                <div class="card-body">
                    <h4 class="mb-4">Leave a Comment</h4>
                    <form method="POST" action="article.php?id=<?php echo $article['id']; ?>">
                        <input type="hidden" name="article_id" value="<?php echo $article['id']; ?>">
                        <div class="mb-3">
                            <label for="author" class="form-label">Name</label>
                            <input type="text" class="form-control" id="author" name="author" required>
                        </div>
                        <div class="mb-3">
                            <label for="comment" class="form-label">Comment</label>
                            <textarea class="form-control" id="comment" name="comment" rows="3" required></textarea>
                        </div>
                        <button type="submit" class="btn btn-primary">Submit</button>
                    </form>

                    <hr>
                    <h5 class="mb-4">Comments</h5>
                    <?php
                    $comments = get_comments($article['id']);
                    foreach ($comments as $comment):
                    ?>
                        <div class="d-flex mb-4">
                            <div class="flex-shrink-0"><img class="rounded-circle" src="https://dummyimage.com/50x50/ced4da/6c757d.jpg" alt="..." /></div>
                            <div class="ms-3">
                                <div class="fw-bold"><?php echo htmlspecialchars($comment['author']); ?></div>
                                <!-- VULNERABILITY #5: Stored XSS in Comments -->
                                <!-- The comment content is echoed back WITHOUT sanitization. -->
                                <?php echo $comment['content']; ?>
                            </div>
                        </div>
                    <?php endforeach; ?>
                </div>
            </div>
        </section>
    </div>
</div>

<?php include 'footer.php'; ?>
