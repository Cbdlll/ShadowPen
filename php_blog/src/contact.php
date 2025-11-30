<?php
include 'header.php';
?>

<div class="row justify-content-center">
    <div class="col-md-8">
        <h1 class="mb-4">Contact Us</h1>

        <?php
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $name = $_POST['name'];
            // VULNERABILITY #7: Reflected XSS via POST parameters
            // The name is echoed back in the success message.
            echo "<div class='alert alert-success'>Thank you, " . $name . "! We have received your message.</div>";
        }
        ?>

        <div class="card">
            <div class="card-body">
                <form method="POST" action="contact.php">
                    <div class="mb-3">
                        <label for="name" class="form-label">Name</label>
                        <input type="text" class="form-control" id="name" name="name" required>
                    </div>
                    <div class="mb-3">
                        <label for="email" class="form-label">Email</label>
                        <input type="email" class="form-control" id="email" name="email" required>
                    </div>
                    <div class="mb-3">
                        <label for="message" class="form-label">Message</label>
                        <textarea class="form-control" id="message" name="message" rows="5" required></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">Send Message</button>
                </form>
            </div>
        </div>
    </div>
</div>

<?php include 'footer.php'; ?>
