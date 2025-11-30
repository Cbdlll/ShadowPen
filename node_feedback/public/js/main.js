document.addEventListener('DOMContentLoaded', () => {
    // DOM XSS Vulnerability
    // Reads location.hash and injects it into the DOM without sanitization
    const hash = window.location.hash;
    if (hash) {
        const filterDisplay = document.getElementById('active-filter');
        if (filterDisplay) {
            // VULNERABLE: innerHTML used with user input
            filterDisplay.innerHTML = "Active Filter: " + decodeURIComponent(hash.substring(1));
        }
    }
});
