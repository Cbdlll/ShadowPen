<?php
include 'header.php';
?>

<div class="row justify-content-center">
    <div class="col-md-8 text-center">
        <h1 class="display-1">404</h1>
        <h2>Page Not Found</h2>
        <p class="lead">
            The requested URL 
            <!-- VULNERABILITY #11 (Bonus): Reflected XSS via URL Path -->
            <!-- The REQUEST_URI is echoed back directly. -->
            <code><?php echo $_SERVER['REQUEST_URI']; ?></code> 
            was not found on this server.
        </p>
        <a href="index.php" class="btn btn-primary">Go Home</a>
    </div>
</div>

<?php include 'footer.php'; ?>
