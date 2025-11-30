import React from 'react';

function TaskCard({ task, onClick }) {
    return (
        <div className="task-card" onClick={onClick}>
            {/* Vulnerability 1: Stored XSS in Title */}
            {/* We use dangerouslySetInnerHTML to allow the XSS to fire when the card is rendered */}
            <div dangerouslySetInnerHTML={{ __html: task.title }} />
            <div style={{ fontSize: '0.8em', color: '#666', marginTop: 5 }}>
                ID: {task.id}
            </div>
        </div>
    );
}

export default TaskCard;
