// src/assets/js/main.js

document.addEventListener('DOMContentLoaded', function () {
    // VULNERABILITY #12 (Bonus): DOM XSS via URL Fragment
    // This script looks for a hash in the URL and sets the innerHTML of an element.
    // Example: http://localhost:8080/#<img src=x onerror=alert(1)>

    if (window.location.hash) {
        var hash = decodeURIComponent(window.location.hash.substring(1));
        // Create a notification div if it doesn't exist
        var notification = document.getElementById('notification-area');
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'notification-area';
            notification.className = 'alert alert-info fixed-bottom m-3';
            document.body.appendChild(notification);
        }

        // VULNERABLE: Setting innerHTML directly from URL fragment
        notification.innerHTML = "Notification: " + hash;
    }
});
