import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Board from './components/Board';
import AdminPanel from './components/AdminPanel';

function App() {
    return (
        <Router>
            <div className="app">
                <nav className="nav">
                    <div className="logo">Team Task Dashboard</div>
                    <div className="links">
                        <Link to="/">Board</Link>
                        <Link to="/admin">Admin Panel</Link>
                    </div>
                </nav>

                <div className="container">
                    <Routes>
                        <Route path="/" element={<Board />} />
                        <Route path="/admin" element={<AdminPanel />} />
                    </Routes>
                </div>
            </div>
        </Router>
    );
}

export default App;
