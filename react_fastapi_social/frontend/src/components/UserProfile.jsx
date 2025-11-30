import { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

function UserProfile() {
    const [profile, setProfile] = useState(null);

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const response = await axios.get(`${API_URL}/api/profile`);
                setProfile(response.data);
            } catch (error) {
                console.error('Error fetching profile:', error);
            }
        };
        fetchProfile();
    }, []);

    if (!profile) return <div>Loading...</div>;

    return (
        <div className="profile">
            <div className="profile-header">
                <div className="profile-avatar">{profile.username[0].toUpperCase()}</div>
                <div className="profile-info">
                    <h2>@{profile.username}</h2>
                    <div className="profile-bio" dangerouslySetInnerHTML={{ __html: profile.bio }} />
                    <a href={profile.website} className="profile-website" target="_blank" rel="noopener noreferrer">
                        Visit Website
                    </a>
                </div>
            </div>

            <div style={{ marginTop: '30px', padding: '20px', background: '#f7f9fc', borderRadius: '8px' }}>
                <h3>Custom Badge</h3>
                <div dangerouslySetInnerHTML={{ __html: profile.customBadge || '<span style="color: gold;">⭐ Default Badge</span>' }} />
            </div>
        </div>
    );
}

export default UserProfile;
