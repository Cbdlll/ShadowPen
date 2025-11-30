import { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

function Post({ post }) {
    const [comments, setComments] = useState(post.comments || []);
    const [commentText, setCommentText] = useState('');
    const [commentAuthor, setCommentAuthor] = useState('');

    const handleAddComment = async () => {
        try {
            const response = await axios.post(`${API_URL}/api/posts/${post.id}/comments`, {
                text: commentText,
                author: commentAuthor,
            });
            setComments([...comments, response.data]);
            setCommentText('');
            setCommentAuthor('');
        } catch (error) {
            console.error('Error adding comment:', error);
        }
    };
    return (
        <div className="post">
            <div className="post-header">
                <div className="post-avatar">{post.author_name[0]?.toUpperCase()}</div>
                <div>
                    <div className="post-author" dangerouslySetInnerHTML={{ __html: post.author_name }} />
                </div>
            </div>
            <div className="post-content" dangerouslySetInnerHTML={{ __html: post.content }} />

            <div className="comments">
                <h4>Comments ({comments.length})</h4>
                {comments.map((comment) => (
                    <div key={comment.id} className="comment">
                        <div className="comment-author">{comment.author}</div>
                        <div className="comment-text" dangerouslySetInnerHTML={{ __html: comment.text }} />
                    </div>
                ))}
                <div className="add-comment">
                    <input
                        type="text"
                        placeholder="Your name"
                        value={commentAuthor}
                        onChange={(e) => setCommentAuthor(e.target.value)}
                    />
                    <input
                        type="text"
                        placeholder="Add a comment..."
                        value={commentText}
                        onChange={(e) => setCommentText(e.target.value)}
                    />
                    <button className="btn" onClick={handleAddComment}>Comment</button>
                </div>
            </div>
        </div>
    );
}

export default Post;
