from django.db import models
from django.contrib.auth.models import User

class WikiPage(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.CharField(max_length=100, blank=True, default='General')

    def __str__(self):
        return self.title

class Comment(models.Model):
    page = models.ForeignKey(WikiPage, related_name='comments', on_delete=models.CASCADE)
    author_name = models.CharField(max_length=100) # Intentionally not linking to User to allow arbitrary names (XSS vector)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author_name} on {self.page}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    signature = models.CharField(max_length=300, blank=True)
    avatar = models.FileField(upload_to='avatars/', blank=True, null=True) # Allows SVG upload

    def __str__(self):
        return self.user.username
