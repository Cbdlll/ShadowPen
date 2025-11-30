<?php
include 'header.php';

// VULNERABILITY #9: Reflected XSS via 'avatar' parameter in image src attribute
// An attacker can break out of the attribute: avatar="><script>...
$avatar = isset($_GET['avatar']) ? $_GET['avatar'] : 'https://dummyimage.com/150x150/ced4da/6c757d.jpg';
?>

<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">User Profile</div>
            <div class="card-body text-center">
                <img src="<?php echo $avatar; ?>" class="rounded-circle mb-3" alt="User Avatar" width="150" height="150">
                
                <h3>Guest User</h3>
                <p class="text-muted">Member since 2023</p>
                
                <div class="mt-4">
                    <h5>Settings</h5>
                    <p>Customize your profile avatar by passing a URL parameter: <code>?avatar=URL</code></p>
                </div>
            </div>
        </div>
    </div>
</div>

<?php include 'footer.php'; ?>
