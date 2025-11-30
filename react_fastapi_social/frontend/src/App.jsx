import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import Feed from './components/Feed';
import UserProfile from './components/UserProfile';
import SearchResults from './components/SearchResults';
import Notification from './components/Notification';
import { useEffect } from 'react';

function App() {
    // Check for hash in URL to show welcome message
    useEffect(() => {
        const hash = window.location.hash.substring(1);
        if (hash) {
            const welcomeDiv = document.getElementById('welcome-message');
            if (welcomeDiv) {
                // Display welcome message
                welcomeDiv.innerHTML = `Welcome back, ${decodeURIComponent(hash)}!`;
            }
        }
    }, []);

    return (
        <Router>
            <div className="app">
                <header className="header">
                    <h1>Social Feed</h1>
                    <nav className="nav">
                        <NavLink to="/" end>Feed</NavLink>
                        <NavLink to="/profile">Profile</NavLink>
                        <NavLink to="/search">Search</NavLink>
                        <NavLink to="/notification">Notifications</NavLink>
                    </nav>
                </header>
                <div id="welcome-message" style={{ padding: '10px', background: '#e7f3ff' }}></div>
                <div className="container">
                    <Routes>
                        <Route path="/" element={<Feed />} />
                        <Route path="/profile" element={<UserProfile />} />
                        <Route path="/search" element={<SearchResults />} />
                        <Route path="/notification" element={<Notification />} />
                    </Routes>
                </div>
            </div>
        </Router>
    );
}

export default App;
