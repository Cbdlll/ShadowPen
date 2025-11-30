import { useEffect, useState } from 'react';

function Notification() {
    const [message, setMessage] = useState('');

    useEffect(() => {
        // Check for message in query params
        const params = new URLSearchParams(window.location.search);
        const msg = params.get('msg');
        if (msg) {
            setMessage(msg);
            // Display notification
            setTimeout(() => {
                const notifDiv = document.getElementById('notification-content');
                if (notifDiv) {
                    notifDiv.innerHTML = decodeURIComponent(msg);
                }
            }, 100);
        }
    }, []);

    return (
        <div>
            <h2>Notifications</h2>
            {message && (
                <div className="notification">
                    <strong>Message:</strong>
                    <div id="notification-content"></div>
                </div>
            )}
            {!message && <p>No new notifications. Try adding ?msg=YourMessage to the URL.</p>}
        </div>
    );
}

export default Notification;
