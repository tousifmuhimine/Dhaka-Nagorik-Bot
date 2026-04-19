"""JSON APIs used by the Next.js frontend."""

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .auth_decorators import login_or_bearer_required
from .models import UserProfile
from .supabase_auth import (
    SupabaseAuthError,
    get_supabase_user,
    supabase_password_login,
    supabase_signup,
    sync_local_user_from_supabase,
)

ALLOWED_ROLES = {"citizen", "authority", "admin"}


def _parse_json_body(request) -> dict[str, Any]:
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError as exc:
        raise SupabaseAuthError("Invalid JSON payload.", status_code=400) from exc

    if not isinstance(data, dict):
        raise SupabaseAuthError("Invalid request body.", status_code=400)
    return data


def _normalize_role(raw_role: str | None) -> str:
    role = (raw_role or "citizen").strip().lower()
    if role not in ALLOWED_ROLES:
        raise SupabaseAuthError("Role must be citizen, authority, or admin.", status_code=400)
    return role


def _serialize_profile(user) -> dict[str, Any]:
    profile = getattr(user, "userprofile", None)
    if not profile:
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.first_name,
            "role": "citizen",
            "approval_status": "approved",
        }

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.first_name,
        "role": profile.role,
        "approval_status": profile.approval_status,
        "city_corporation": profile.city_corporation,
        "ward_number": profile.ward_number,
        "thana": profile.thana,
        "department": profile.department,
        "employee_id": profile.employee_id,
        "phone_number": profile.phone_number,
        "access_reason": profile.access_reason,
    }


def _profile_data_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "city_corporation": (payload.get("city_corporation") or "").strip(),
        "ward_number": payload.get("ward_number"),
        "thana": (payload.get("thana") or "").strip(),
        "department": (payload.get("department") or "").strip(),
        "employee_id": (payload.get("employee_id") or "").strip(),
        "phone_number": (payload.get("phone_number") or "").strip(),
        "access_reason": (payload.get("access_reason") or "").strip(),
    }


def _validate_role_fields(role: str, profile_data: dict[str, Any]) -> None:
    if role in {"authority", "admin"}:
        required_fields = {
            "department": "Department is required for authority/admin access.",
            "employee_id": "Employee ID is required for authority/admin access.",
            "phone_number": "Phone number is required for authority/admin access.",
            "access_reason": "Access reason is required for authority/admin access.",
        }
        for field_name, error_message in required_fields.items():
            if not (profile_data.get(field_name) or "").strip():
                raise SupabaseAuthError(error_message, status_code=400)

    if role == "authority":
        city = (profile_data.get("city_corporation") or "").strip()
        ward = profile_data.get("ward_number")
        thana = (profile_data.get("thana") or "").strip()

        if not city:
            raise SupabaseAuthError("City corporation is required for authority access.", status_code=400)
        if ward in (None, ""):
            raise SupabaseAuthError("Ward number is required for authority access.", status_code=400)
        if not thana:
            raise SupabaseAuthError("Thana/neighborhood label is required for authority access.", status_code=400)

        try:
            ward_int = int(ward)
        except (TypeError, ValueError) as exc:
            raise SupabaseAuthError("Ward number must be a valid integer.", status_code=400) from exc

        duplicate = UserProfile.objects.filter(
            role="authority",
            city_corporation=city,
            ward_number=ward_int,
            approval_status__in={"pending", "approved"},
        ).exists()
        if duplicate:
            raise SupabaseAuthError(
                "An authority account already exists or is pending for this ward.",
                status_code=400,
            )


def _json_error(exc: SupabaseAuthError) -> JsonResponse:
    return JsonResponse({"success": False, "error": str(exc)}, status=exc.status_code)


def _extract_access_token(request) -> str:
    authorization = (request.headers.get("Authorization") or "").strip()
    if authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token:
            return token

    payload = _parse_json_body(request)
    token = (payload.get("access_token") or "").strip()
    if token:
        return token

    raise SupabaseAuthError("Missing access token.", status_code=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_signup(request):
    """Create a user in Supabase Auth and mirror profile metadata locally."""
    try:
        payload = _parse_json_body(request)
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        full_name = (payload.get("full_name") or "").strip()
        role = _normalize_role(payload.get("role"))

        if not email:
            raise SupabaseAuthError("Email is required.", status_code=400)
        if not password:
            raise SupabaseAuthError("Password is required.", status_code=400)
        if not full_name:
            raise SupabaseAuthError("Full name is required.", status_code=400)

        profile_data = _profile_data_from_payload(payload)
        _validate_role_fields(role, profile_data)

        metadata = {
            "full_name": full_name,
            "role": role,
            **profile_data,
        }
        signup_result = supabase_signup(
            email=email,
            password=password,
            metadata=metadata,
        )

        supabase_user = signup_result.get("user")
        if not isinstance(supabase_user, dict):
            raise SupabaseAuthError("Supabase did not return a user payload.", status_code=500)

        user = sync_local_user_from_supabase(
            supabase_user,
            role=role,
            profile_data=profile_data,
        )

        message = "Account created successfully."
        if role in {"authority", "admin"}:
            message = "Registration submitted. An approved admin must review your account before login."

        session = signup_result.get("session") or {}
        return JsonResponse(
            {
                "success": True,
                "message": message,
                "user": _serialize_profile(user),
                "access_token": session.get("access_token"),
                "refresh_token": session.get("refresh_token"),
                "expires_in": session.get("expires_in"),
            },
            status=201,
        )
    except SupabaseAuthError as exc:
        return _json_error(exc)


@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    """Authenticate with Supabase and return bearer tokens for API usage."""
    try:
        payload = _parse_json_body(request)
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        if not email or not password:
            raise SupabaseAuthError("Email and password are required.", status_code=400)

        login_result = supabase_password_login(email=email, password=password)
        access_token = (login_result.get("access_token") or "").strip()
        if not access_token:
            raise SupabaseAuthError("Supabase login did not return an access token.", status_code=500)

        supabase_user = login_result.get("user")
        if not isinstance(supabase_user, dict):
            supabase_user = get_supabase_user(access_token)

        user = sync_local_user_from_supabase(supabase_user)
        profile = getattr(user, "userprofile", None)
        if profile and profile.approval_status == "pending":
            raise SupabaseAuthError("This account is waiting for admin approval.", status_code=403)
        if profile and profile.approval_status == "rejected":
            raise SupabaseAuthError(
                "This signup request was rejected. Please contact an admin.",
                status_code=403,
            )

        return JsonResponse(
            {
                "success": True,
                "user": _serialize_profile(user),
                "access_token": access_token,
                "refresh_token": login_result.get("refresh_token"),
                "expires_in": login_result.get("expires_in"),
            }
        )
    except SupabaseAuthError as exc:
        return _json_error(exc)


@csrf_exempt
@require_http_methods(["POST"])
def api_logout(_request):
    """Client-side logout endpoint for symmetry."""
    return JsonResponse({"success": True})


@csrf_exempt
@require_http_methods(["POST"])
def api_session_login(request):
    """Create a Django session after Supabase bearer authentication."""
    try:
        token = _extract_access_token(request)
        supabase_user = get_supabase_user(token)
        user = sync_local_user_from_supabase(supabase_user)

        profile = getattr(user, "userprofile", None)
        if profile and profile.approval_status == "pending":
            raise SupabaseAuthError("This account is waiting for admin approval.", status_code=403)
        if profile and profile.approval_status == "rejected":
            raise SupabaseAuthError(
                "This signup request was rejected. Please contact an admin.",
                status_code=403,
            )

        login(request, user)
        return JsonResponse({"success": True, "user": _serialize_profile(user)})
    except SupabaseAuthError as exc:
        return _json_error(exc)


@csrf_exempt
@require_http_methods(["POST"])
def api_session_logout(request):
    """Destroy any backend Django session tied to the browser."""
    logout(request)
    return JsonResponse({"success": True})


@login_or_bearer_required
@require_http_methods(["GET"])
def api_me(request):
    """Return the authenticated user profile."""
    return JsonResponse({"success": True, "user": _serialize_profile(request.user)})
