import { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

import Post from './Post';

function SearchResults() {
    const [query, setQuery] = useState('');
    const [searchResult, setSearchResult] = useState(null);

    const handleSearch = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/search?q=${encodeURIComponent(query)}`);
            setSearchResult(response.data);
        } catch (error) {
            console.error('Error searching:', error);
        }
    };

    return (
        <div>
            <h2>Search</h2>
            <div className="search-box">
                <input
                    type="text"
                    placeholder="Search..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                />
                <p style={{ fontSize: '0.9rem', color: '#666', marginTop: '5px' }}>
                    Tip: Search by post content or author name.
                </p>
                <button className="btn" onClick={handleSearch} style={{ marginTop: '10px' }}>
                    Search
                </button>
            </div>

            {searchResult && (
                <div className="search-results">
                    <div className="search-query">
                        You searched for: <span dangerouslySetInnerHTML={{ __html: searchResult.query }} />
                    </div>

                    {searchResult.results.length > 0 ? (
                        <div className="feed">
                            {searchResult.results.map((post) => (
                                <Post key={post.id} post={post} />
                            ))}
                        </div>
                    ) : (
                        <p>No results found.</p>
                    )}
                </div>
            )}
        </div>
    );
}

export default SearchResults;
