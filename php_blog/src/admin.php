<?php
include 'header.php';

// Simple hardcoded login
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = $_POST['username'];
    $password = $_POST['password'];

    if ($username === 'admin' && $password === 'admin123') {
        setcookie('username', 'admin', time() + 3600, "/");
        header("Location: index.php");
        exit;
    } else {
        $error = "Invalid credentials";
    }
}
?>

<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card mt-5">
            <div class="card-header">Admin Login</div>
            <div class="card-body">
                <?php if (isset($error)): ?>
                    <div class="alert alert-danger"><?php echo $error; ?></div>
                <?php endif; ?>

                <!-- VULNERABILITY #8: Reflected XSS via 'msg' parameter -->
                <!-- The 'msg' parameter is echoed back directly. -->
                <?php
                if (isset($_GET['msg'])) {
                    echo "<div class='alert alert-warning'>" . $_GET['msg'] . "</div>";
                }
                ?>

                <form method="POST" action="admin.php">
                    <div class="mb-3">
                        <label for="username" class="form-label">Username</label>
                        <input type="text" class="form-control" id="username" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Login</button>
                </form>
            </div>
        </div>
    </div>
</div>

<?php include 'footer.php'; ?>
