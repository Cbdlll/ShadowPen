</div> <!-- End Container -->

<footer class="footer text-center text-muted">
    <div class="container">
        <p>&copy; <?php echo date("Y"); ?> TechInsights Blog. All rights reserved.</p>
        <p class="small">
            You are currently viewing: 
            <script>
                // VULNERABILITY #2: DOM XSS via document.write and location.pathname
                // This script takes the current path and writes it to the DOM.
                // An attacker can craft a URL like http://localhost:8080/index.php/"><script>alert(1)</script>
                // Note: Modern browsers might URL encode pathname, but this is a classic pattern.
                // A more reliable DOM XSS here would be using a URL parameter or fragment handled by JS.
                // Let's use a URL parameter 'ref' for "Referrer" tracking that gets written.
                
                const urlParams = new URLSearchParams(window.location.search);
                const ref = urlParams.get('ref');
                if (ref) {
                     document.write("Referrer: " + ref);
                } else {
                    document.write(window.location.pathname);
                }
            </script>
        </p>
    </div>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="assets/js/main.js"></script>
</body>
</html>
