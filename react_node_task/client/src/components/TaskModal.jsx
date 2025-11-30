import React, { useState, useEffect } from 'react';
import axios from 'axios';

function TaskModal({ task, onClose, onUpdate }) {
    const [comments, setComments] = useState([]);
    const [newComment, setNewComment] = useState('');
    const [author, setAuthor] = useState('Anonymous');
    const [webhookUrl, setWebhookUrl] = useState('');
    const [webhookMsg, setWebhookMsg] = useState('');

    useEffect(() => {
        fetchComments();
    }, [task.id]);

    const fetchComments = async () => {
        const res = await axios.get(`/api/tasks/${task.id}/comments`);
        setComments(res.data);
    };

    const handleAddComment = async (e) => {
        e.preventDefault();
        await axios.post(`/api/tasks/${task.id}/comments`, {
            body: newComment,
            author: author
        });
        setNewComment('');
        fetchComments();
    };

    const handleWebhook = async (e) => {
        e.preventDefault();
        const res = await axios.post('/api/webhooks', { url: webhookUrl });
        // Vulnerability 7: Reflected XSS via Webhook response
        // The server returns HTML in 'message', we render it raw.
        setWebhookMsg(res.data.message);
    };

    // Vulnerability 3: Custom "Markdown" parser that is vulnerable
    const parseNotes = (text) => {
        if (!text) return '';
        // Simple replace for bold, but doesn't strip scripts
        return text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    {/* Vulnerability 1 again: Title */}
                    <h2 dangerouslySetInnerHTML={{ __html: task.title }}></h2>
                    <button onClick={onClose} className="btn" style={{ background: '#ccc' }}>X</button>
                </div>

                <div className="input-group">
                    <label>Description</label>
                    {/* Vulnerability 2: Stored XSS in Description */}
                    <div
                        style={{ padding: 10, background: '#f9f9f9', border: '1px solid #eee' }}
                        dangerouslySetInnerHTML={{ __html: task.description }}
                    />
                </div>

                <div className="input-group">
                    <label>Attachments (Vulnerable Links)</label>
                    {/* Vulnerability 6: javascript: URI allowed */}
                    <span>No attachments</span>
                    {/* Dynamic link if we had one in DB, but static demonstrates the point for "Attachment" concept */}
                </div>

                <hr />

                <h3>Comments</h3>
                <div className="comments-list" style={{ maxHeight: 200, overflowY: 'auto', marginBottom: 20 }}>
                    {comments.map(comment => (
                        <div key={comment.id} style={{ borderBottom: '1px solid #eee', padding: '5px 0' }}>
                            {/* Vulnerability 5: Author Name Stored XSS */}
                            <strong dangerouslySetInnerHTML={{ __html: comment.author + ':' }}></strong>
                            {/* Vulnerability 4: Comment Body Stored XSS */}
                            <span style={{ marginLeft: 10 }} dangerouslySetInnerHTML={{ __html: comment.body }}></span>
                        </div>
                    ))}
                </div>

                <form onSubmit={handleAddComment}>
                    <div className="input-group">
                        <input
                            type="text"
                            value={author}
                            onChange={e => setAuthor(e.target.value)}
                            placeholder="Your Name"
                        />
                    </div>
                    <div className="input-group">
                        <textarea
                            value={newComment}
                            onChange={e => setNewComment(e.target.value)}
                            placeholder="Write a comment..."
                        ></textarea>
                    </div>
                    <button type="submit" className="btn">Post Comment</button>
                </form>

                <hr />

                <div style={{ marginTop: 20, padding: 10, background: '#e6fcff' }}>
                    <h4>Webhook Integration</h4>
                    <form onSubmit={handleWebhook}>
                        <input
                            type="text"
                            value={webhookUrl}
                            onChange={e => setWebhookUrl(e.target.value)}
                            placeholder="https://example.com/webhook"
                            style={{ width: '70%', marginRight: 10 }}
                        />
                        <button type="submit" className="btn">Save</button>
                    </form>
                    {webhookMsg && (
                        // Vulnerability 7: Reflected XSS
                        <div style={{ marginTop: 10 }} dangerouslySetInnerHTML={{ __html: webhookMsg }}></div>
                    )}
                </div>

            </div>
        </div>
    );
}

export default TaskModal;
