import React, { useState, useEffect } from 'react';
import axios from 'axios';

function AdminPanel() {
    const [logs, setLogs] = useState([]);
    const [stats, setStats] = useState(null);

    useEffect(() => {
        fetchLogs();
        fetchStats();
    }, []);

    const fetchLogs = async () => {
        const res = await axios.get('/api/admin/logs');
        setLogs(res.data);
    };

    const fetchStats = async () => {
        const res = await axios.get('/api/admin/stats');
        setStats(res.data);

        // Vulnerability 8: JSON Injection (Simulated)
        // In a real scenario, this might be embedded in the initial HTML.
        // Here we just show that we are handling data that could be dangerous if we were doing SSR or specific DOM manipulation.
        // But to make it "real" in this SPA context, let's say we inject it into a script tag dynamically (rare but possible)
        // or just render it.
        // Let's stick to the requirement: "JSON注入: 构造特殊的 JSON 破坏前端解析 or 渲染逻辑"
        // If 'latest_task_title' contains HTML/Script, and we render it:
    };

    return (
        <div className="admin-panel">
            <h1>Admin Dashboard</h1>

            {stats && (
                <div className="stats-card" style={{ background: 'white', padding: 20, marginBottom: 20 }}>
                    <h3>System Stats</h3>
                    <p>Total Tasks: {stats.total_tasks}</p>
                    {/* Vulnerability 8: If this title has XSS, it fires here too */}
                    <p>Latest Task: <span dangerouslySetInnerHTML={{ __html: stats.latest_task_title }}></span></p>
                </div>
            )}

            <div className="logs-section">
                <h3>Security Logs (Recent Activity)</h3>
                <table style={{ width: '100%', borderCollapse: 'collapse', background: 'white' }}>
                    <thead>
                        <tr style={{ background: '#eee', textAlign: 'left' }}>
                            <th style={{ padding: 10 }}>ID</th>
                            <th style={{ padding: 10 }}>Action</th>
                            <th style={{ padding: 10 }}>Details</th>
                            <th style={{ padding: 10 }}>Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {logs.map(log => (
                            <tr key={log.id} style={{ borderBottom: '1px solid #eee' }}>
                                <td style={{ padding: 10 }}>{log.id}</td>
                                <td style={{ padding: 10 }}>{log.action}</td>
                                {/* Vulnerability 10: Blind XSS Trigger */}
                                {/* When Admin views this page, the 'details' (which contains the task title viewed) is rendered raw */}
                                <td style={{ padding: 10 }} dangerouslySetInnerHTML={{ __html: log.details }}></td>
                                <td style={{ padding: 10 }}>{log.timestamp}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default AdminPanel;
