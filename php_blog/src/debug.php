<?php
include 'header.php';
?>

<div class="row">
    <div class="col-md-12">
        <h1 class="mb-4">Debug Information</h1>
        <div class="alert alert-secondary">
            <p>This page displays request information for debugging purposes.</p>
        </div>

        <div class="card">
            <div class="card-header">Request Headers</div>
            <div class="card-body">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Header</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php
                        $headers = getallheaders();
                        foreach ($headers as $name => $value) {
                            // VULNERABILITY #10: Reflected XSS via HTTP Headers
                            // Headers like Referer or custom headers are echoed back.
                            echo "<tr>";
                            echo "<td>" . htmlspecialchars($name) . "</td>";
                            echo "<td>" . $value . "</td>"; // VULNERABLE: Value is not escaped
                            echo "</tr>";
                        }
                        ?>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<?php include 'footer.php'; ?>
