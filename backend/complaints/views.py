"""Views for the complaints system."""

from io import BytesIO
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .area_routing import same_service_area, service_area_label
from .forms import ComplaintForm, ComplaintUpdateForm, LoginForm, SignUpForm
from .models import ChatAttachment, Complaint, ComplaintAttachment, ComplaintUpdate, UserProfile, log_complaint_activity
from .services.complaint_submission_service import generate_documents_and_notify
from .services.document_storage_service import DocumentStorageService
from .services.email_service import ComplaintEmailService

ALLOWED_IMAGE_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
}
MAX_ATTACHMENTS_PER_COMPLAINT = 5
MAX_ATTACHMENT_SIZE = 8 * 1024 * 1024


def _get_profile(user):
    """Return the attached profile when available."""
    return getattr(user, 'userprofile', None)


def _is_approved_admin(user):
    """Return True when the user is an approved admin."""
    profile = _get_profile(user)
    return bool(
        profile
        and profile.role == 'admin'
        and profile.approval_status == 'approved'
    )


def _is_approved_authority(user):
    """Return True when the user is an approved authority."""
    profile = _get_profile(user)
    return bool(
        profile
        and profile.role == 'authority'
        and profile.approval_status == 'approved'
    )


def _can_access_complaint(user, complaint):
    """Return whether the given user can view the complaint."""
    if complaint.citizen_id == user.id:
        return True
    if _is_approved_admin(user):
        return True
    profile = _get_profile(user)
    return bool(
        profile
        and profile.role == 'authority'
        and profile.approval_status == 'approved'
        and same_service_area(
            left_city_corporation=profile.city_corporation,
            left_ward_number=profile.ward_number,
            left_thana=profile.thana,
            right_city_corporation=complaint.city_corporation,
            right_ward_number=complaint.ward_number,
            right_thana=complaint.thana,
        )
    )


def _validate_complaint_attachments(uploaded_files):
    """Validate direct image uploads for manual complaints."""
    if len(uploaded_files) > MAX_ATTACHMENTS_PER_COMPLAINT:
        return f'Please upload no more than {MAX_ATTACHMENTS_PER_COMPLAINT} photos.'

    for uploaded in uploaded_files:
        if uploaded.content_type not in ALLOWED_IMAGE_TYPES:
            return f'{uploaded.name} is not a supported image type.'
        if uploaded.size > MAX_ATTACHMENT_SIZE:
            return f'{uploaded.name} is larger than 8 MB.'
    return ''


def home(request):
    """Home page - redirect to dashboard if logged in."""
    if request.user.is_authenticated:
        profile = _get_profile(request.user)
        if profile and profile.approval_status != 'approved':
            logout(request)
            messages.warning(request, 'Your account is waiting for admin approval.')
            return redirect('login')
        if profile:
            if profile.role == 'citizen':
                return redirect('citizen_dashboard')
            if profile.role == 'authority':
                return redirect('authority_dashboard')
            if profile.role == 'admin':
                return redirect('admin_dashboard')
    return redirect('login')


def signup(request):
    """User signup page."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data['role']
            needs_approval = role in {'authority', 'admin'}
            UserProfile.objects.create(
                user=user,
                role=role,
                city_corporation=(form.cleaned_data.get('city_corporation') or '').strip(),
                ward_number=form.cleaned_data.get('ward_number'),
                thana=(form.cleaned_data.get('thana') or '').strip() or None,
                department=(form.cleaned_data.get('department') or '').strip(),
                employee_id=(form.cleaned_data.get('employee_id') or '').strip(),
                phone_number=(form.cleaned_data.get('phone_number') or '').strip(),
                access_reason=(form.cleaned_data.get('access_reason') or '').strip(),
                approval_status='pending' if needs_approval else 'approved',
            )
            if needs_approval:
                messages.success(
                    request,
                    'Registration submitted. An approved admin must review your account before you can log in.',
                )
            else:
                messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
    else:
        form = SignUpForm()

    return render(request, 'complaints/signup.html', {
        'form': form,
        'auth_mode': 'signup',
    })


def login_view(request):
    """User login page."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            password = form.cleaned_data['password']

            try:
                existing_user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                existing_user = None

            if existing_user and not existing_user.is_active:
                profile = _get_profile(existing_user)
                if profile and profile.approval_status == 'pending':
                    messages.warning(request, 'This account is waiting for admin approval.')
                elif profile and profile.approval_status == 'rejected':
                    messages.error(request, 'This signup request was rejected. Please contact an admin.')
                else:
                    messages.error(request, 'This account is inactive.')
            else:
                username = existing_user.username if existing_user else email
                user = authenticate(request, username=username, password=password)
                if user is not None:
                    profile = _get_profile(user)
                    if profile and profile.approval_status != 'approved':
                        messages.warning(request, 'Your account is waiting for admin approval.')
                    else:
                        login(request, user)
                        messages.success(request, f'Welcome, {user.first_name or user.username}!')
                        return redirect('home')
                else:
                    messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()

    return render(request, 'complaints/login.html', {
        'form': form,
        'auth_mode': 'login',
    })


def logout_view(request):
    """User logout."""
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('login')


@login_required(login_url='login')
def citizen_dashboard(request):
    """Citizen dashboard - file and track complaints."""
    profile = _get_profile(request.user)
    if not profile or profile.role != 'citizen':
        messages.error(request, 'You do not have access to this page.')
        return redirect('home')

    complaints = request.user.complaints.select_related('assigned_authority').all()

    if request.method == 'POST':
        uploaded_files = request.FILES.getlist('photos')
        form = ComplaintForm(request.POST)
        attachment_error = _validate_complaint_attachments(uploaded_files)

        if attachment_error:
            messages.error(request, attachment_error)
        elif form.is_valid():
            complaint = form.save(commit=False)
            complaint.citizen = request.user
            complaint.status = 'submitted'
            complaint.save()
            attachments = []
            for uploaded in uploaded_files:
                attachments.append(ComplaintAttachment.objects.create(
                    complaint=complaint,
                    file=uploaded,
                    original_name=uploaded.name,
                    content_type=uploaded.content_type or '',
                ))
            log_complaint_activity(
                complaint,
                'filed',
                actor=request.user,
                message='Complaint filed by citizen.',
            )
            delivery_result = generate_documents_and_notify(complaint, attachments=attachments)

            if delivery_result['documents_generated'] and delivery_result['authority_email_sent']:
                messages.success(request, 'Complaint filed successfully. It was routed to the assigned area authority, and a copy was sent to your email.')
            elif delivery_result['documents_generated']:
                messages.success(request, 'Complaint filed successfully. The DOCX/PDF files were generated for download.')
                if delivery_result['email_error']:
                    messages.warning(request, f"Complaint notifications were incomplete: {delivery_result['email_error']}")
            else:
                messages.success(request, 'Complaint filed successfully.')
                if delivery_result['email_error']:
                    messages.warning(request, delivery_result['email_error'])
            return redirect('citizen_dashboard')
    else:
        form = ComplaintForm()

    context = {
        'form': form,
        'complaints': complaints,
        'total': complaints.count(),
        'resolved': complaints.filter(status='resolved').count(),
        'pending_total': complaints.exclude(status='resolved').count(),
    }
    return render(request, 'complaints/citizen_dashboard.html', context)


@login_required(login_url='login')
def complaint_detail(request, id):
    """View complaint details, timeline, and notes."""
    complaint = get_object_or_404(
        Complaint.objects.select_related('citizen', 'assigned_authority'),
        id=id,
    )
    if not _can_access_complaint(request.user, complaint):
        messages.error(request, 'You do not have permission to view this complaint.')
        return redirect('home')

    profile = _get_profile(request.user)
    is_owner = complaint.citizen_id == request.user.id
    is_admin = bool(profile and profile.role == 'admin' and profile.approval_status == 'approved')
    is_area_authority = bool(
        profile
        and profile.role == 'authority'
        and profile.approval_status == 'approved'
        and same_service_area(
            left_city_corporation=profile.city_corporation,
            left_ward_number=profile.ward_number,
            left_thana=profile.thana,
            right_city_corporation=complaint.city_corporation,
            right_ward_number=complaint.ward_number,
            right_thana=complaint.thana,
        )
    )
    is_assigned_authority = complaint.assigned_authority_id == request.user.id

    can_add_note = is_owner or is_admin or is_area_authority
    can_acknowledge = (
        is_area_authority
        and complaint.status == 'submitted'
        and (
            complaint.assigned_authority_id is None
            or complaint.assigned_authority_id == request.user.id
        )
    )
    can_mark_resolved = is_assigned_authority and complaint.status in {'acknowledged', 'in_progress'}
    can_confirm_resolution = is_owner and complaint.status == 'awaiting_citizen_confirmation'

    if request.method == 'POST' and can_add_note:
        form = ComplaintUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.complaint = complaint
            update.updated_by = request.user
            update.save()
            log_complaint_activity(
                complaint,
                'note_added',
                actor=request.user,
                message=update.message,
            )
            messages.success(request, 'Update added successfully.')
            return redirect('complaint_detail', id=complaint.id)
    else:
        form = ComplaintUpdateForm() if can_add_note else None

    source_session = complaint.source_chat_sessions.first()
    evidence_images = list(
        complaint.attachments.filter(content_type__startswith='image/').order_by('uploaded_at')
    )
    if source_session:
        evidence_images.extend(list(
            ChatAttachment.objects.filter(
                message__chat_session=source_session,
                message__role='user',
                content_type__startswith='image/',
            ).order_by('uploaded_at')
        ))
    evidence_images.sort(key=lambda image: image.uploaded_at)

    context = {
        'complaint': complaint,
        'complaint_service_area': service_area_label(
            complaint.city_corporation,
            complaint.ward_number,
            complaint.thana,
        ),
        'updates': complaint.updates.select_related('updated_by').all(),
        'activities': complaint.activities.select_related('actor').all(),
        'form': form,
        'can_add_note': can_add_note,
        'can_acknowledge': can_acknowledge,
        'can_mark_resolved': can_mark_resolved,
        'can_confirm_resolution': can_confirm_resolution,
        'evidence_images': evidence_images,
    }
    return render(request, 'complaints/complaint_detail.html', context)


@login_required(login_url='login')
def download_complaint_document(request, id, fmt):
    """Download generated complaint documents."""
    complaint = get_object_or_404(Complaint, id=id)

    if not _can_access_complaint(request.user, complaint):
        raise Http404('Document not available')

    if fmt == 'docx':
        target_path = complaint.generated_docx_path
    elif fmt == 'pdf':
        target_path = complaint.generated_pdf_path
    else:
        raise Http404('Unknown document format')

    if not target_path:
        raise Http404('Document not available')

    document_storage = DocumentStorageService()
    if not document_storage.exists(target_path):
        raise Http404('Document file not found')

    return FileResponse(
        BytesIO(document_storage.read_bytes(target_path)),
        as_attachment=True,
        filename=document_storage.filename(target_path),
    )


@login_required(login_url='login')
def authority_dashboard(request):
    """Authority dashboard - manage assigned complaints."""
    profile = _get_profile(request.user)
    if not profile or profile.role != 'authority' or profile.approval_status != 'approved':
        messages.error(request, 'You do not have access to this page.')
        return redirect('home')

    complaints = Complaint.objects.select_related(
        'citizen',
        'assigned_authority',
    )
    if profile.city_corporation and profile.ward_number:
        complaints = complaints.filter(
            city_corporation=profile.city_corporation,
            ward_number=profile.ward_number,
        )
    else:
        complaints = complaints.filter(thana__iexact=profile.thana)
    assigned = complaints.filter(assigned_authority=request.user)

    context = {
        'complaints': complaints,
        'assigned': assigned,
        'service_area': service_area_label(profile.city_corporation, profile.ward_number, profile.thana),
        'total': complaints.count(),
        'pending': complaints.exclude(status='resolved').count(),
        'awaiting_confirmation': complaints.filter(status='awaiting_citizen_confirmation').count(),
    }
    return render(request, 'complaints/authority_dashboard.html', context)


@login_required(login_url='login')
def admin_dashboard(request):
    """Admin dashboard - manage all complaints and users."""
    profile = _get_profile(request.user)
    if not profile or profile.role != 'admin' or profile.approval_status != 'approved':
        messages.error(request, 'You do not have access to this page.')
        return redirect('home')

    complaints = Complaint.objects.select_related('citizen', 'assigned_authority').all()
    users = User.objects.all()

    search = request.GET.get('search', '').strip()
    if search:
        complaint_filters = (
            Q(description__icontains=search)
            | Q(area__icontains=search)
            | Q(thana__icontains=search)
            | Q(city_corporation__icontains=search)
            | Q(citizen__first_name__icontains=search)
            | Q(citizen__email__icontains=search)
        )
        if search.isdigit():
            complaint_filters |= Q(ward_number=int(search))
        complaints = complaints.filter(complaint_filters)

    status = request.GET.get('status', '').strip()
    if status:
        complaints = complaints.filter(status=status)

    pending_requests = UserProfile.objects.filter(
        role__in=['authority', 'admin'],
        approval_status='pending',
    ).select_related('user').order_by('created_at')

    context = {
        'complaints': complaints,
        'users': users,
        'pending_requests': pending_requests,
        'total_complaints': Complaint.objects.count(),
        'total_users': users.count(),
        'resolved': Complaint.objects.filter(status='resolved').count(),
        'pending': Complaint.objects.exclude(status='resolved').count(),
        'awaiting_confirmation': Complaint.objects.filter(status='awaiting_citizen_confirmation').count(),
        'search': search,
        'status': status,
    }
    return render(request, 'complaints/admin_dashboard.html', context)


@login_required(login_url='login')
@require_POST
def approve_access_request(request, profile_id):
    """Approve a pending authority/admin signup."""
    if not _is_approved_admin(request.user):
        messages.error(request, 'You do not have access to this action.')
        return redirect('home')

    profile = get_object_or_404(UserProfile.objects.select_related('user'), id=profile_id)
    if profile.role == 'citizen':
        messages.error(request, 'Citizen accounts do not require approval.')
        return redirect('admin_dashboard')

    if profile.role == 'authority' and profile.city_corporation and profile.ward_number:
        duplicate_approved = UserProfile.objects.filter(
            role='authority',
            approval_status='approved',
            city_corporation=profile.city_corporation,
            ward_number=profile.ward_number,
        ).exclude(id=profile.id)
        if duplicate_approved.exists():
            messages.error(
                request,
                f'Another approved authority already covers {profile.service_area}. Reject or reassign this request first.',
            )
            return redirect('admin_dashboard')

    profile.approval_status = 'approved'
    profile.approved_by = request.user
    profile.approved_at = timezone.now()
    profile.rejected_at = None
    profile.save(update_fields=['approval_status', 'approved_by', 'approved_at', 'rejected_at', 'updated_at'])

    profile.user.is_active = True
    profile.user.save(update_fields=['is_active'])

    messages.success(request, f'{profile.user.email} has been approved.')
    return redirect('admin_dashboard')


@login_required(login_url='login')
@require_POST
def reject_access_request(request, profile_id):
    """Reject a pending authority/admin signup."""
    if not _is_approved_admin(request.user):
        messages.error(request, 'You do not have access to this action.')
        return redirect('home')

    profile = get_object_or_404(UserProfile.objects.select_related('user'), id=profile_id)
    if profile.role == 'citizen':
        messages.error(request, 'Citizen accounts do not require approval.')
        return redirect('admin_dashboard')

    profile.approval_status = 'rejected'
    profile.approved_by = None
    profile.approved_at = None
    profile.rejected_at = timezone.now()
    profile.save(update_fields=['approval_status', 'approved_by', 'approved_at', 'rejected_at', 'updated_at'])

    profile.user.is_active = False
    profile.user.save(update_fields=['is_active'])

    messages.success(request, f'{profile.user.email} has been rejected.')
    return redirect('admin_dashboard')


@login_required(login_url='login')
@require_POST
def acknowledge_complaint(request, id):
    """Allow an area authority to acknowledge a complaint."""
    complaint = get_object_or_404(Complaint, id=id)
    profile = _get_profile(request.user)
    if not (
        profile
        and profile.role == 'authority'
        and profile.approval_status == 'approved'
        and same_service_area(
            left_city_corporation=profile.city_corporation,
            left_ward_number=profile.ward_number,
            left_thana=profile.thana,
            right_city_corporation=complaint.city_corporation,
            right_ward_number=complaint.ward_number,
            right_thana=complaint.thana,
        )
    ):
        messages.error(request, 'You do not have access to acknowledge this complaint.')
        return redirect('home')

    if complaint.assigned_authority_id and complaint.assigned_authority_id != request.user.id:
        messages.error(request, 'This complaint is already acknowledged by another authority.')
        return redirect('complaint_detail', id=complaint.id)

    complaint.assigned_authority = request.user
    complaint.status = 'acknowledged'
    complaint.acknowledged_at = timezone.now()
    complaint.save(update_fields=['assigned_authority', 'status', 'acknowledged_at', 'updated_at'])
    log_complaint_activity(
        complaint,
        'acknowledged',
        actor=request.user,
        message=f'Acknowledged for {complaint.service_area}.',
    )

    messages.success(request, 'Complaint acknowledged successfully.')
    return redirect('complaint_detail', id=complaint.id)


@login_required(login_url='login')
@require_POST
def request_resolution_confirmation(request, id):
    """Mark the complaint as solved and wait for citizen confirmation."""
    complaint = get_object_or_404(Complaint, id=id)
    profile = _get_profile(request.user)
    if not (
        profile
        and profile.role == 'authority'
        and profile.approval_status == 'approved'
        and complaint.assigned_authority_id == request.user.id
    ):
        messages.error(request, 'Only the assigned authority can submit resolution for confirmation.')
        return redirect('home')

    if complaint.status not in {'acknowledged', 'in_progress'}:
        messages.error(request, 'This complaint cannot be marked solved yet.')
        return redirect('complaint_detail', id=complaint.id)

    complaint.status = 'awaiting_citizen_confirmation'
    complaint.resolution_requested_at = timezone.now()
    complaint.resolved_at = None
    complaint.save(update_fields=['status', 'resolution_requested_at', 'resolved_at', 'updated_at'])
    log_complaint_activity(
        complaint,
        'resolution_requested',
        actor=request.user,
        message='Authority marked the complaint as solved and requested citizen confirmation.',
    )

    messages.success(request, 'Resolution submitted. The citizen must confirm before the complaint is closed.')
    return redirect('complaint_detail', id=complaint.id)


@login_required(login_url='login')
@require_POST
def confirm_resolution(request, id):
    """Allow the citizen to confirm the authority's resolution."""
    complaint = get_object_or_404(Complaint, id=id)
    if complaint.citizen_id != request.user.id:
        messages.error(request, 'Only the reporting citizen can confirm this resolution.')
        return redirect('home')

    if complaint.status != 'awaiting_citizen_confirmation':
        messages.error(request, 'This complaint is not waiting for citizen confirmation.')
        return redirect('complaint_detail', id=complaint.id)

    now = timezone.now()
    complaint.status = 'resolved'
    complaint.citizen_confirmed_at = now
    complaint.resolved_at = now
    complaint.save(update_fields=['status', 'citizen_confirmed_at', 'resolved_at', 'updated_at'])
    log_complaint_activity(
        complaint,
        'citizen_confirmed',
        actor=request.user,
        message='Citizen confirmed the complaint has been resolved.',
    )

    messages.success(request, 'Thank you. The complaint is now marked as resolved.')
    return redirect('complaint_detail', id=complaint.id)


@login_required(login_url='login')
@require_POST
def reopen_resolution(request, id):
    """Allow the citizen to reject the submitted resolution."""
    complaint = get_object_or_404(Complaint, id=id)
    if complaint.citizen_id != request.user.id:
        messages.error(request, 'Only the reporting citizen can reopen this complaint.')
        return redirect('home')

    if complaint.status != 'awaiting_citizen_confirmation':
        messages.error(request, 'This complaint is not waiting for citizen confirmation.')
        return redirect('complaint_detail', id=complaint.id)

    complaint.status = 'acknowledged'
    complaint.resolution_requested_at = None
    complaint.citizen_confirmed_at = None
    complaint.resolved_at = None
    complaint.save(update_fields=['status', 'resolution_requested_at', 'citizen_confirmed_at', 'resolved_at', 'updated_at'])
    log_complaint_activity(
        complaint,
        'citizen_reopened',
        actor=request.user,
        message='Citizen requested more work before closing the complaint.',
    )

    messages.warning(request, 'The complaint has been reopened for the assigned authority.')
    return redirect('complaint_detail', id=complaint.id)


@login_required(login_url='login')
@require_POST
def remind_assigned_authority(request, id):
    """Send an email reminder for an unresolved complaint."""
    if not _is_approved_admin(request.user):
        messages.error(request, 'You do not have access to this action.')
        return redirect('home')

    complaint = get_object_or_404(Complaint.objects.select_related('assigned_authority'), id=id)
    if complaint.status == 'resolved':
        messages.error(request, 'Resolved complaints do not need reminders.')
        return redirect('admin_dashboard')

    service = ComplaintEmailService()
    sent, error_message = service.send_authority_reminder(complaint)
    if sent:
        complaint.last_reminder_sent_at = timezone.now()
        complaint.save(update_fields=['last_reminder_sent_at', 'updated_at'])
        log_complaint_activity(
            complaint,
            'reminder_sent',
            actor=request.user,
            message='Admin sent a reminder email to the assigned authority.',
        )
        messages.success(request, 'Reminder email sent to the assigned authority.')
    else:
        messages.error(request, error_message)

    return redirect('admin_dashboard')
