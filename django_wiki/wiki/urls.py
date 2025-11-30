from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('page/<int:pk>/', views.page_detail, name='page_detail'),
    path('create/', views.page_create, name='page_create'),
    path('edit/<int:pk>/', views.page_edit, name='page_edit'),
    path('profile/', views.profile, name='profile'),
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
]
