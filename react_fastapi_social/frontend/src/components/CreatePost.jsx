import { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

function CreatePost({ onPostCreated }) {
    const [content, setContent] = useState('');
    const [authorName, setAuthorName] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await axios.post(`${API_URL}/api/posts`, {
                content,
                author_name: authorName,
            });
            setContent('');
            setAuthorName('');
            onPostCreated();
        } catch (error) {
            console.error('Error creating post:', error);
        }
    };

    return (
        <div className="create-post">
            <h2>Create a Post</h2>
            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label>Your Name:</label>
                    <input
                        type="text"
                        value={authorName}
                        onChange={(e) => setAuthorName(e.target.value)}
                        required
                    />
                </div>
                <div className="form-group">
                    <label>What's on your mind?</label>
                    <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        required
                    />
                </div>
                <button type="submit" className="btn">Post</button>
            </form>
        </div>
    );
}

export default CreatePost;
