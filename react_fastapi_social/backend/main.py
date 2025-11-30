from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid

app = FastAPI()

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory Database
posts = []
users = {
    "admin": {
        "username": "admin",
        "bio": "<b>System Administrator</b>",
        "website": "https://example.com"
    }
}

class Comment(BaseModel):
    id: str
    text: str
    author: str

class Post(BaseModel):
    id: Optional[str] = None
    content: str
    author_name: str
    comments: List[Comment] = []

class PostCreate(BaseModel):
    content: str
    author_name: str

class CommentCreate(BaseModel):
    text: str
    author: str

@app.get("/api/posts", response_model=List[Post])
def get_posts():
    return posts[::-1]

@app.post("/api/posts", response_model=Post)
def create_post(post: PostCreate):
    new_post = Post(
        id=str(uuid.uuid4()),
        content=post.content,
        author_name=post.author_name,
        comments=[]
    )
    posts.append(new_post)
    return new_post

@app.post("/api/posts/{post_id}/comments", response_model=Comment)
def create_comment(post_id: str, comment: CommentCreate):
    for post in posts:
        if post.id == post_id:
            new_comment = Comment(
                id=str(uuid.uuid4()),
                text=comment.text,
                author=comment.author
            )
            post.comments.append(new_comment)
            return new_comment
    raise HTTPException(status_code=404, detail="Post not found")

@app.get("/api/search")
def search(q: str):
    results = [
        post for post in posts 
        if q.lower() in post.content.lower() or q.lower() in post.author_name.lower()
    ]
    return {"query": q, "results": results}

@app.get("/api/profile")
def get_profile():
    return users["admin"]

@app.get("/api/error")
def trigger_error():
    return "<html><body><h1>Error: Something went wrong</h1></body></html>"

# Initialize some data
import random

def generate_mock_data():
    mock_users = [
        {"name": "Alice", "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Alice"},
        {"name": "Bob", "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Bob"},
        {"name": "Charlie", "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Charlie"},
        {"name": "Diana", "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Diana"},
        {"name": "Ethan", "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Ethan"},
        {"name": "Fiona", "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Fiona"},
        {"name": "George", "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=George"},
        {"name": "Hannah", "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Hannah"},
    ]

    post_templates = [
        "Just finished a great hiking trip! The views were amazing. 🏔️",
        "Anyone tried the new coffee shop on Main St? Their latte is to die for! ☕",
        "Working on a new React project. Hooks are so powerful! ⚛️",
        "Can't believe it's already Friday. Time flies! 🚀",
        "Reading a fascinating book about history. Highly recommend 'Sapiens'. 📚",
        "Beautiful sunset today. Nature is the best artist. 🌅",
        "Coding late into the night. The bug must be squashed! 🐛",
        "Just adopted a new puppy! Meet Max. 🐶",
        "Learning Python and FastAPI. It's so fast and intuitive! 🐍",
        "Had a delicious sushi dinner. 🍣",
        "Exploring the city. So many hidden gems. 🏙️",
        "Music is life. What are you listening to right now? 🎧",
        "Gym time! Gotta stay fit. 💪",
        "Dreaming of my next vacation. Maybe Japan? 🇯🇵",
        "Just baked some cookies. Who wants one? 🍪"
    ]

    comment_templates = [
        "That sounds awesome!",
        "Totally agree!",
        "Wow, nice!",
        "Thanks for sharing.",
        "I need to try that too.",
        "Great photo!",
        "Keep it up!",
        "Interesting perspective.",
        "Love it!",
        "So cool!"
    ]

    for i in range(20):
        user = random.choice(mock_users)
        post_content = random.choice(post_templates)
        
        num_comments = random.randint(0, 5)
        post_comments = []
        for _ in range(num_comments):
            comment_user = random.choice(mock_users)
            comment_text = random.choice(comment_templates)
            post_comments.append(Comment(
                id=str(uuid.uuid4()),
                text=comment_text,
                author=comment_user["name"]
            ))

        posts.append(Post(
            id=str(uuid.uuid4()),
            content=post_content,
            author_name=user["name"],
            comments=post_comments
        ))

generate_mock_data()
