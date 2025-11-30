from django.contrib import admin
from .models import WikiPage, Comment, UserProfile

admin.site.register(WikiPage)
admin.site.register(Comment)
admin.site.register(UserProfile)
