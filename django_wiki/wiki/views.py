from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import WikiPage, Comment, UserProfile
from django.db.models import Q

def index(request):
    query = request.GET.get('q', '')
    if query:
        pages = WikiPage.objects.filter(Q(title__icontains=query) | Q(content__icontains=query))
    else:
        pages = WikiPage.objects.all()
    
    # Vulnerability #5: Search Query Reflected XSS
    # Passed to template and will be rendered with |safe
    
    return render(request, 'wiki/index.html', {'pages': pages, 'query': query})

def page_detail(request, pk):
    page = get_object_or_404(WikiPage, pk=pk)
    
    # Vulnerability #4: Breadcrumb Reflected XSS via URL parameter
    breadcrumb = request.GET.get('crumb', 'Home')
    
    if request.method == 'POST':
        # Handle comment submission
        author_name = request.POST.get('author_name', 'Anonymous')
        content = request.POST.get('content', '')
        Comment.objects.create(page=page, author_name=author_name, content=content)
        return redirect('page_detail', pk=pk)

    comments = page.comments.all().order_by('-created_at')
    
    return render(request, 'wiki/page_detail.html', {
        'page': page,
        'comments': comments,
        'breadcrumb': breadcrumb,
    })

@login_required
def page_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category = request.POST.get('category', 'General')
        page = WikiPage.objects.create(title=title, content=content, category=category, author=request.user)
        return redirect('page_detail', pk=page.pk)
    return render(request, 'wiki/page_form.html', {'action': 'Create'})

@login_required
def page_edit(request, pk):
    page = get_object_or_404(WikiPage, pk=pk)
    if request.method == 'POST':
        page.title = request.POST.get('title')
        page.content = request.POST.get('content')
        page.category = request.POST.get('category')
        page.save()
        return redirect('page_detail', pk=page.pk)
    return render(request, 'wiki/page_form.html', {'page': page, 'action': 'Edit'})

@login_required
def profile(request):
    user = request.user
    if not hasattr(user, 'profile'):
        UserProfile.objects.create(user=user)
    
    if request.method == 'POST':
        user.profile.bio = request.POST.get('bio', '')
        user.profile.signature = request.POST.get('signature', '')
        if 'avatar' in request.FILES:
            user.profile.avatar = request.FILES['avatar']
        user.profile.save()
        return redirect('profile')
        
    return render(request, 'wiki/profile.html', {'user': user})

def user_login(request):
    if request.method == 'POST':
        from django.contrib.auth import authenticate, login
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            error = 'Invalid username or password'
            return render(request, 'wiki/login.html', {'error': error})
    return render(request, 'wiki/login.html')

def user_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email', '')
        
        if User.objects.filter(username=username).exists():
            error = 'Username already exists'
            return render(request, 'wiki/register.html', {'error': error})
        
        user = User.objects.create_user(username=username, password=password, email=email)
        UserProfile.objects.create(user=user)
        
        from django.contrib.auth import login
        login(request, user)
        return redirect('/')
    return render(request, 'wiki/register.html')

def user_logout(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('/')

