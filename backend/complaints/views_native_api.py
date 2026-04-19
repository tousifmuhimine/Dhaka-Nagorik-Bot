"""Native JSON APIs for dashboards and complaint lifecycle screens."""

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .area_routing import CITY_CORPORATION_CHOICES, WARD_NUMBER_CHOICES, same_service_area, service_area_label
from .auth_decorators import login_or_bearer_required
from .forms import ComplaintForm, ComplaintUpdateForm
from .models import ChatAttachment, Complaint, ComplaintAttachment, UserProfile, log_complaint_activity
from .services.complaint_submission_service import generate_documents_and_notify
from .services.email_service import ComplaintEmailService
from .views import _validate_complaint_attachments


def _parse_json_body(request) -> dict[str, Any]:
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _profile(user) -> UserProfile | None:
    return getattr(user, "userprofile", None)


def _is_admin(profile: UserProfile | None) -> bool:
    return bool(profile and profile.role == "admin" and profile.approval_status == "approved")


def _is_authority(profile: UserProfile | None) -> bool:
    return bool(profile and profile.role == "authority" and profile.approval_status == "approved")


def _user_display(user: User | None) -> dict[str, Any] | None:
    if not user:
        return None
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.get_full_name() or user.username,
        "username": user.username,
    }


def _json_error(message: str, *, status: int = 400) -> JsonResponse:
    return JsonResponse({"success": False, "error": message}, status=status)


def _serialize_complaint(complaint: Complaint) -> dict[str, Any]:
    return {
        "id": complaint.id,
        "category": complaint.category,
        "category_display": complaint.get_category_display(),
        "city_corporation": complaint.city_corporation,
        "ward_number": complaint.ward_number,
        "thana": complaint.thana,
        "area": complaint.area,
        "service_area": service_area_label(complaint.city_corporation, complaint.ward_number, complaint.thana),
        "description": complaint.description,
        "status": complaint.status,
        "status_display": complaint.get_status_display(),
        "created_at": complaint.created_at.isoformat(),
        "updated_at": complaint.updated_at.isoformat(),
        "acknowledged_at": complaint.acknowledged_at.isoformat() if complaint.acknowledged_at else None,
        "resolution_requested_at": complaint.resolution_requested_at.isoformat() if complaint.resolution_requested_at else None,
        "citizen_confirmed_at": complaint.citizen_confirmed_at.isoformat() if complaint.citizen_confirmed_at else None,
        "resolved_at": complaint.resolved_at.isoformat() if complaint.resolved_at else None,
        "last_reminder_sent_at": complaint.last_reminder_sent_at.isoformat() if complaint.last_reminder_sent_at else None,
        "email_sent_at": complaint.email_sent_at.isoformat() if complaint.email_sent_at else None,
        "email_error": complaint.email_error,
        "citizen": _user_display(complaint.citizen),
        "assigned_authority": _user_display(complaint.assigned_authority),
        "generated_docx_url": reverse("download_complaint_document", args=[complaint.id, "docx"]) if complaint.generated_docx_path else None,
        "generated_pdf_url": reverse("download_complaint_document", args=[complaint.id, "pdf"]) if complaint.generated_pdf_path else None,
    }


def _serialize_profile_request(profile: UserProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "role": profile.role,
        "approval_status": profile.approval_status,
        "city_corporation": profile.city_corporation,
        "ward_number": profile.ward_number,
        "thana": profile.thana,
        "service_area": profile.service_area,
        "department": profile.department,
        "employee_id": profile.employee_id,
        "phone_number": profile.phone_number,
        "access_reason": profile.access_reason,
        "created_at": profile.created_at.isoformat(),
        "user": _user_display(profile.user),
    }


def _serialize_form_errors(form) -> dict[str, list[str]]:
    return {field: [str(error) for error in errors] for field, errors in form.errors.items()}


def _is_area_authority(profile: UserProfile | None, complaint: Complaint) -> bool:
    return bool(
        _is_authority(profile)
        and same_service_area(
            left_city_corporation=profile.city_corporation,
            left_ward_number=profile.ward_number,
            left_thana=profile.thana,
            right_city_corporation=complaint.city_corporation,
            right_ward_number=complaint.ward_number,
            right_thana=complaint.thana,
        )
    )


def _can_access_complaint(user, profile: UserProfile | None, complaint: Complaint) -> bool:
    if complaint.citizen_id == user.id:
        return True
    if _is_admin(profile):
        return True
    return _is_area_authority(profile, complaint)


def _detail_permissions(user, profile: UserProfile | None, complaint: Complaint) -> dict[str, bool]:
    is_owner = complaint.citizen_id == user.id
    is_admin = _is_admin(profile)
    is_area_authority = _is_area_authority(profile, complaint)
    is_assigned_authority = complaint.assigned_authority_id == user.id

    return {
        "is_owner": is_owner,
        "is_admin": is_admin,
        "is_area_authority": is_area_authority,
        "is_assigned_authority": is_assigned_authority,
        "can_add_note": is_owner or is_admin or is_area_authority,
        "can_acknowledge": (
            is_area_authority
            and complaint.status == "submitted"
            and (
                complaint.assigned_authority_id is None
                or complaint.assigned_authority_id == user.id
            )
        ),
        "can_mark_resolved": is_assigned_authority and complaint.status in {"acknowledged", "in_progress"},
        "can_confirm_resolution": is_owner and complaint.status == "awaiting_citizen_confirmation",
    }


def _serialize_activity(activity) -> dict[str, Any]:
    return {
        "id": activity.id,
        "event_type": activity.event_type,
        "event_type_display": activity.get_event_type_display(),
        "message": activity.message,
        "created_at": activity.created_at.isoformat(),
        "actor": _user_display(activity.actor),
    }


def _serialize_update(update) -> dict[str, Any]:
    return {
        "id": update.id,
        "message": update.message,
        "status_change": update.status_change,
        "created_at": update.created_at.isoformat(),
        "updated_by": _user_display(update.updated_by),
    }


def _serialize_evidence(image, request) -> dict[str, Any]:
    image_url = image.file.url if image.file else ""
    if image_url and not image_url.startswith("http"):
        image_url = request.build_absolute_uri(image_url)
    return {
        "id": image.id,
        "name": image.original_name,
        "url": image_url,
        "uploaded_at": image.uploaded_at.isoformat(),
        "content_type": image.content_type,
    }


def _complaint_detail_payload(request, complaint: Complaint) -> dict[str, Any]:
    profile = _profile(request.user)
    permissions = _detail_permissions(request.user, profile, complaint)

    source_session = complaint.source_chat_sessions.first()
    evidence_images = list(
        complaint.attachments.filter(content_type__startswith="image/").order_by("uploaded_at")
    )
    if source_session:
        evidence_images.extend(
            list(
                ChatAttachment.objects.filter(
                    message__chat_session=source_session,
                    message__role="user",
                    content_type__startswith="image/",
                ).order_by("uploaded_at")
            )
        )
    evidence_images.sort(key=lambda image: image.uploaded_at)

    return {
        "complaint": _serialize_complaint(complaint),
        "permissions": permissions,
        "activities": [_serialize_activity(item) for item in complaint.activities.select_related("actor").all()],
        "updates": [_serialize_update(item) for item in complaint.updates.select_related("updated_by").all()],
        "evidence_images": [_serialize_evidence(item, request) for item in evidence_images],
    }


@login_or_bearer_required
@require_http_methods(["GET"])
def api_citizen_dashboard(request):
    profile = _profile(request.user)
    if not profile or profile.role != "citizen":
        return _json_error("You do not have access to this page.", status=403)

    complaints = request.user.complaints.select_related("assigned_authority").all()
    return JsonResponse(
        {
            "success": True,
            "stats": {
                "total": complaints.count(),
                "resolved": complaints.filter(status="resolved").count(),
                "pending_total": complaints.exclude(status="resolved").count(),
            },
            "complaints": [_serialize_complaint(item) for item in complaints],
            "meta": {
                "category_choices": [{"value": value, "label": label} for value, label in Complaint.CATEGORY_CHOICES],
                "city_corporation_choices": [{"value": value, "label": label} for value, label in CITY_CORPORATION_CHOICES],
                "ward_choices": [{"value": value, "label": label} for value, label in WARD_NUMBER_CHOICES],
            },
        }
    )


@csrf_exempt
@login_or_bearer_required
@require_http_methods(["POST"])
def api_citizen_create_complaint(request):
    profile = _profile(request.user)
    if not profile or profile.role != "citizen":
        return _json_error("You do not have access to this action.", status=403)

    payload = request.POST if request.content_type and request.content_type.startswith("multipart/form-data") else _parse_json_body(request)
    uploaded_files = request.FILES.getlist("photos")

    attachment_error = _validate_complaint_attachments(uploaded_files)
    if attachment_error:
        return _json_error(attachment_error, status=400)

    form = ComplaintForm(payload)
    if not form.is_valid():
        return JsonResponse({"success": False, "errors": _serialize_form_errors(form)}, status=400)

    complaint = form.save(commit=False)
    complaint.citizen = request.user
    complaint.status = "submitted"
    complaint.save()

    attachments = []
    for uploaded in uploaded_files:
        attachments.append(
            ComplaintAttachment.objects.create(
                complaint=complaint,
                file=uploaded,
                original_name=uploaded.name,
                content_type=uploaded.content_type or "",
            )
        )

    log_complaint_activity(
        complaint,
        "filed",
        actor=request.user,
        message="Complaint filed by citizen.",
    )
    delivery_result = generate_documents_and_notify(complaint, attachments=attachments)

    return JsonResponse(
        {
            "success": True,
            "complaint": _serialize_complaint(complaint),
            "delivery": delivery_result,
            "message": "Complaint filed successfully.",
        },
        status=201,
    )


@login_or_bearer_required
@require_http_methods(["GET"])
def api_authority_dashboard(request):
    profile = _profile(request.user)
    if not _is_authority(profile):
        return _json_error("You do not have access to this page.", status=403)

    complaints = Complaint.objects.select_related("citizen", "assigned_authority")
    if profile.city_corporation and profile.ward_number:
        complaints = complaints.filter(
            city_corporation=profile.city_corporation,
            ward_number=profile.ward_number,
        )
    else:
        complaints = complaints.filter(thana__iexact=profile.thana)

    assigned = complaints.filter(assigned_authority=request.user)
    return JsonResponse(
        {
            "success": True,
            "service_area": service_area_label(profile.city_corporation, profile.ward_number, profile.thana),
            "stats": {
                "total": complaints.count(),
                "pending": complaints.exclude(status="resolved").count(),
                "awaiting_confirmation": complaints.filter(status="awaiting_citizen_confirmation").count(),
                "assigned_count": assigned.count(),
            },
            "complaints": [_serialize_complaint(item) for item in complaints],
        }
    )


@login_or_bearer_required
@require_http_methods(["GET"])
def api_admin_dashboard(request):
    profile = _profile(request.user)
    if not _is_admin(profile):
        return _json_error("You do not have access to this page.", status=403)

    complaints = Complaint.objects.select_related("citizen", "assigned_authority").all()

    search = (request.GET.get("search") or "").strip()
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

    status = (request.GET.get("status") or "").strip()
    if status:
        complaints = complaints.filter(status=status)

    pending_requests = (
        UserProfile.objects.filter(role__in=["authority", "admin"], approval_status="pending")
        .select_related("user")
        .order_by("created_at")
    )

    return JsonResponse(
        {
            "success": True,
            "stats": {
                "total_complaints": Complaint.objects.count(),
                "total_users": User.objects.count(),
                "resolved": Complaint.objects.filter(status="resolved").count(),
                "pending": Complaint.objects.exclude(status="resolved").count(),
                "awaiting_confirmation": Complaint.objects.filter(status="awaiting_citizen_confirmation").count(),
            },
            "search": search,
            "status": status,
            "status_choices": [{"value": value, "label": label} for value, label in Complaint.STATUS_CHOICES],
            "complaints": [_serialize_complaint(item) for item in complaints],
            "pending_requests": [_serialize_profile_request(item) for item in pending_requests],
        }
    )


@csrf_exempt
@login_or_bearer_required
@require_http_methods(["POST"])
def api_admin_approve_access_request(request, profile_id: int):
    profile = _profile(request.user)
    if not _is_admin(profile):
        return _json_error("You do not have access to this action.", status=403)

    request_profile = get_object_or_404(UserProfile.objects.select_related("user"), id=profile_id)
    if request_profile.role == "citizen":
        return _json_error("Citizen accounts do not require approval.", status=400)

    if request_profile.role == "authority" and request_profile.city_corporation and request_profile.ward_number:
        duplicate_approved = UserProfile.objects.filter(
            role="authority",
            approval_status="approved",
            city_corporation=request_profile.city_corporation,
            ward_number=request_profile.ward_number,
        ).exclude(id=request_profile.id)
        if duplicate_approved.exists():
            return _json_error(
                f"Another approved authority already covers {request_profile.service_area}.",
                status=400,
            )

    now = timezone.now()
    request_profile.approval_status = "approved"
    request_profile.approved_by = request.user
    request_profile.approved_at = now
    request_profile.rejected_at = None
    request_profile.save(update_fields=["approval_status", "approved_by", "approved_at", "rejected_at", "updated_at"])

    request_profile.user.is_active = True
    request_profile.user.save(update_fields=["is_active"])

    return JsonResponse({
        "success": True,
        "message": f"{request_profile.user.email} has been approved.",
        "request": _serialize_profile_request(request_profile),
    })


@csrf_exempt
@login_or_bearer_required
@require_http_methods(["POST"])
def api_admin_reject_access_request(request, profile_id: int):
    profile = _profile(request.user)
    if not _is_admin(profile):
        return _json_error("You do not have access to this action.", status=403)

    request_profile = get_object_or_404(UserProfile.objects.select_related("user"), id=profile_id)
    if request_profile.role == "citizen":
        return _json_error("Citizen accounts do not require approval.", status=400)

    now = timezone.now()
    request_profile.approval_status = "rejected"
    request_profile.approved_by = None
    request_profile.approved_at = None
    request_profile.rejected_at = now
    request_profile.save(update_fields=["approval_status", "approved_by", "approved_at", "rejected_at", "updated_at"])

    request_profile.user.is_active = False
    request_profile.user.save(update_fields=["is_active"])

    return JsonResponse({
        "success": True,
        "message": f"{request_profile.user.email} has been rejected.",
        "request": _serialize_profile_request(request_profile),
    })


@csrf_exempt
@login_or_bearer_required
@require_http_methods(["POST"])
def api_admin_remind_assigned_authority(request, id: int):
    profile = _profile(request.user)
    if not _is_admin(profile):
        return _json_error("You do not have access to this action.", status=403)

    complaint = get_object_or_404(Complaint.objects.select_related("assigned_authority"), id=id)
    if complaint.status == "resolved":
        return _json_error("Resolved complaints do not need reminders.", status=400)

    service = ComplaintEmailService()
    sent, error_message = service.send_authority_reminder(complaint)
    if not sent:
        return _json_error(error_message or "Failed to send reminder.", status=400)

    complaint.last_reminder_sent_at = timezone.now()
    complaint.save(update_fields=["last_reminder_sent_at", "updated_at"])
    log_complaint_activity(
        complaint,
        "reminder_sent",
        actor=request.user,
        message="Admin sent a reminder email to the assigned authority.",
    )

    return JsonResponse(
        {
            "success": True,
            "message": "Reminder email sent to the assigned authority.",
            "complaint": _serialize_complaint(complaint),
        }
    )


@login_or_bearer_required
@require_http_methods(["GET"])
def api_complaint_detail(request, id: int):
    complaint = get_object_or_404(
        Complaint.objects.select_related("citizen", "assigned_authority"),
        id=id,
    )
    profile = _profile(request.user)
    if not _can_access_complaint(request.user, profile, complaint):
        return _json_error("You do not have permission to view this complaint.", status=403)

    return JsonResponse({"success": True, **_complaint_detail_payload(request, complaint)})


@csrf_exempt
@login_or_bearer_required
@require_http_methods(["POST"])
def api_complaint_add_note(request, id: int):
    complaint = get_object_or_404(Complaint.objects.select_related("citizen", "assigned_authority"), id=id)
    profile = _profile(request.user)
    permissions = _detail_permissions(request.user, profile, complaint)
    if not permissions["can_add_note"]:
        return _json_error("You do not have permission to add a note.", status=403)

    payload = _parse_json_body(request)
    form = ComplaintUpdateForm(payload)
    if not form.is_valid():
        return JsonResponse({"success": False, "errors": _serialize_form_errors(form)}, status=400)

    update = form.save(commit=False)
    update.complaint = complaint
    update.updated_by = request.user
    update.save()

    log_complaint_activity(
        complaint,
        "note_added",
        actor=request.user,
        message=update.message,
    )

    return JsonResponse(
        {
            "success": True,
            "message": "Update added successfully.",
            "update": _serialize_update(update),
            "detail": _complaint_detail_payload(request, complaint),
        }
    )


@csrf_exempt
@login_or_bearer_required
@require_http_methods(["POST"])
def api_complaint_acknowledge(request, id: int):
    complaint = get_object_or_404(Complaint, id=id)
    profile = _profile(request.user)
    if not _is_area_authority(profile, complaint):
        return _json_error("You do not have access to acknowledge this complaint.", status=403)

    if complaint.assigned_authority_id and complaint.assigned_authority_id != request.user.id:
        return _json_error("This complaint is already acknowledged by another authority.", status=400)

    complaint.assigned_authority = request.user
    complaint.status = "acknowledged"
    complaint.acknowledged_at = timezone.now()
    complaint.save(update_fields=["assigned_authority", "status", "acknowledged_at", "updated_at"])

    log_complaint_activity(
        complaint,
        "acknowledged",
        actor=request.user,
        message=f"Acknowledged for {complaint.service_area}.",
    )

    return JsonResponse({"success": True, "message": "Complaint acknowledged successfully.", "complaint": _serialize_complaint(complaint)})


@csrf_exempt
@login_or_bearer_required
@require_http_methods(["POST"])
def api_complaint_request_resolution(request, id: int):
    complaint = get_object_or_404(Complaint, id=id)
    profile = _profile(request.user)
    if not (_is_authority(profile) and complaint.assigned_authority_id == request.user.id):
        return _json_error("Only the assigned authority can submit resolution for confirmation.", status=403)

    if complaint.status not in {"acknowledged", "in_progress"}:
        return _json_error("This complaint cannot be marked solved yet.", status=400)

    complaint.status = "awaiting_citizen_confirmation"
    complaint.resolution_requested_at = timezone.now()
    complaint.resolved_at = None
    complaint.save(update_fields=["status", "resolution_requested_at", "resolved_at", "updated_at"])

    log_complaint_activity(
        complaint,
        "resolution_requested",
        actor=request.user,
        message="Authority marked the complaint as solved and requested citizen confirmation.",
    )

    return JsonResponse(
        {
            "success": True,
            "message": "Resolution submitted. The citizen must confirm before the complaint is closed.",
            "complaint": _serialize_complaint(complaint),
        }
    )


@csrf_exempt
@login_or_bearer_required
@require_http_methods(["POST"])
def api_complaint_confirm_resolution(request, id: int):
    complaint = get_object_or_404(Complaint, id=id)
    if complaint.citizen_id != request.user.id:
        return _json_error("Only the reporting citizen can confirm this resolution.", status=403)

    if complaint.status != "awaiting_citizen_confirmation":
        return _json_error("This complaint is not waiting for citizen confirmation.", status=400)

    now = timezone.now()
    complaint.status = "resolved"
    complaint.citizen_confirmed_at = now
    complaint.resolved_at = now
    complaint.save(update_fields=["status", "citizen_confirmed_at", "resolved_at", "updated_at"])

    log_complaint_activity(
        complaint,
        "citizen_confirmed",
        actor=request.user,
        message="Citizen confirmed the complaint has been resolved.",
    )

    return JsonResponse(
        {
            "success": True,
            "message": "Thank you. The complaint is now marked as resolved.",
            "complaint": _serialize_complaint(complaint),
        }
    )


@csrf_exempt
@login_or_bearer_required
@require_http_methods(["POST"])
def api_complaint_reopen(request, id: int):
    complaint = get_object_or_404(Complaint, id=id)
    if complaint.citizen_id != request.user.id:
        return _json_error("Only the reporting citizen can reopen this complaint.", status=403)

    if complaint.status != "awaiting_citizen_confirmation":
        return _json_error("This complaint is not waiting for citizen confirmation.", status=400)

    complaint.status = "acknowledged"
    complaint.resolution_requested_at = None
    complaint.citizen_confirmed_at = None
    complaint.resolved_at = None
    complaint.save(update_fields=["status", "resolution_requested_at", "citizen_confirmed_at", "resolved_at", "updated_at"])

    log_complaint_activity(
        complaint,
        "citizen_reopened",
        actor=request.user,
        message="Citizen requested more work before closing the complaint.",
    )

    return JsonResponse(
        {
            "success": True,
            "message": "The complaint has been reopened for the assigned authority.",
            "complaint": _serialize_complaint(complaint),
        }
    )
