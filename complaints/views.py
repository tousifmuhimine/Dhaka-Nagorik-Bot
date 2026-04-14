"""Views for the complaints system."""

from pathlib import Path

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse, Http404
from .models import ChatAttachment, Complaint, ComplaintUpdate, UserProfile
from .forms import SignUpForm, LoginForm, ComplaintForm, ComplaintUpdateForm


def home(request):
    """Home page - redirect to dashboard if logged in."""
    if request.user.is_authenticated:
        try:
            profile = request.user.userprofile
            if profile.role == 'citizen':
                return redirect('citizen_dashboard')
            elif profile.role == 'authority':
                return redirect('authority_dashboard')
            elif profile.role == 'admin':
                return redirect('admin_dashboard')
        except UserProfile.DoesNotExist:
            pass
    return redirect('login')


def signup(request):
    """User signup page."""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create citizen profile by default
            UserProfile.objects.create(user=user, role='citizen')
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = SignUpForm()
    
    return render(request, 'complaints/signup.html', {'form': form})


def login_view(request):
    """User login page."""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            try:
                user = User.objects.get(email=email)
                user = authenticate(request, username=user.username, password=password)
                
                if user is not None:
                    login(request, user)
                    messages.success(request, f'Welcome, {user.first_name}!')
                    return redirect('home')
                else:
                    messages.error(request, 'Invalid password.')
            except User.DoesNotExist:
                messages.error(request, 'Email not found.')
    else:
        form = LoginForm()
    
    return render(request, 'complaints/login.html', {'form': form})


def logout_view(request):
    """User logout."""
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('login')


@login_required(login_url='login')
def citizen_dashboard(request):
    """Citizen dashboard - file and track complaints."""
    try:
        profile = request.user.userprofile
        if profile.role != 'citizen':
            messages.error(request, 'You do not have access to this page.')
            return redirect('home')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('login')
    
    complaints = request.user.complaints.all()
    
    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.citizen = request.user
            complaint.save()
            messages.success(request, 'Complaint filed successfully!')
            return redirect('citizen_dashboard')
    else:
        form = ComplaintForm()
    
    context = {
        'form': form,
        'complaints': complaints,
        'total': complaints.count(),
        'resolved': complaints.filter(status='resolved').count(),
    }
    return render(request, 'complaints/citizen_dashboard.html', context)


@login_required(login_url='login')
def complaint_detail(request, id):
    """View complaint details and updates."""
    complaint = get_object_or_404(Complaint, id=id)
    
    # Check permissions
    is_owner = complaint.citizen == request.user
    is_assigned = complaint.assigned_authority == request.user
    is_admin = request.user.userprofile.role == 'admin'
    
    if not (is_owner or is_assigned or is_admin):
        messages.error(request, 'You do not have permission to view this complaint.')
        return redirect('home')
    
    # Add update
    if request.method == 'POST' and (is_assigned or is_admin):
        form = ComplaintUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.complaint = complaint
            update.updated_by = request.user
            update.save()
            
            # Update status if changed
            if update.status_change:
                complaint.status = update.status_change
                complaint.save()
            
            messages.success(request, 'Update added successfully!')
            return redirect('complaint_detail', id=complaint.id)
    else:
        form = ComplaintUpdateForm() if (is_assigned or is_admin) else None

    source_session = complaint.source_chat_sessions.first()
    evidence_images = []
    if source_session:
        evidence_images = ChatAttachment.objects.filter(
            message__chat_session=source_session,
            message__role='user',
            content_type__startswith='image/',
        ).order_by('uploaded_at')
    
    context = {
        'complaint': complaint,
        'updates': complaint.updates.all(),
        'form': form,
        'can_update': is_assigned or is_admin,
        'evidence_images': evidence_images,
    }
    return render(request, 'complaints/complaint_detail.html', context)


@login_required(login_url='login')
def download_complaint_document(request, id, fmt):
    """Download generated complaint documents."""
    complaint = get_object_or_404(Complaint, id=id)

    is_owner = complaint.citizen == request.user
    is_assigned = complaint.assigned_authority == request.user
    is_admin = request.user.userprofile.role == 'admin'
    if not (is_owner or is_assigned or is_admin):
        raise Http404('Document not available')

    if fmt == 'docx':
        target_path = complaint.generated_docx_path
    elif fmt == 'pdf':
        target_path = complaint.generated_pdf_path
    else:
        raise Http404('Unknown document format')

    if not target_path:
        raise Http404('Document not available')

    resolved = Path(target_path).resolve()
    allowed_root = Path(settings.DOCUMENT_OUTPUT_DIR).resolve()
    if allowed_root not in resolved.parents:
        raise Http404('Document path is invalid')
    if not resolved.exists():
        raise Http404('Document file not found')

    return FileResponse(open(resolved, 'rb'), as_attachment=True, filename=resolved.name)


@login_required(login_url='login')
def authority_dashboard(request):
    """Authority dashboard - manage assigned complaints."""
    try:
        profile = request.user.userprofile
        if profile.role != 'authority':
            messages.error(request, 'You do not have access to this page.')
            return redirect('home')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('login')
    
    complaints = Complaint.objects.filter(thana=profile.thana)
    assigned = request.user.assigned_complaints.all()
    
    context = {
        'complaints': complaints,
        'assigned': assigned,
        'thana': profile.thana,
        'total': complaints.count(),
        'pending': complaints.filter(status__in=['submitted', 'under_review']).count(),
    }
    return render(request, 'complaints/authority_dashboard.html', context)


@login_required(login_url='login')
def admin_dashboard(request):
    """Admin dashboard - manage all complaints and users."""
    try:
        profile = request.user.userprofile
        if profile.role != 'admin':
            messages.error(request, 'You do not have access to this page.')
            return redirect('home')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('login')
    
    complaints = Complaint.objects.all()
    users = User.objects.all()
    
    # Search
    search = request.GET.get('search')
    if search:
        complaints = complaints.filter(
            Q(description__icontains=search) |
            Q(area__icontains=search) |
            Q(citizen__first_name__icontains=search)
        )
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        complaints = complaints.filter(status=status)
    
    context = {
        'complaints': complaints,
        'users': users,
        'total_complaints': Complaint.objects.count(),
        'total_users': users.count(),
        'resolved': Complaint.objects.filter(status='resolved').count(),
        'pending': Complaint.objects.filter(status__in=['submitted', 'under_review']).count(),
        'search': search,
        'status': status,
    }
    return render(request, 'complaints/admin_dashboard.html', context)
