"""Supabase auth helpers for API login/signup and bearer token validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction

from .models import UserProfile

AUTH_TIMEOUT_SECONDS = 20


@dataclass
class SupabaseAuthError(Exception):
    """Raised when Supabase auth operations fail."""

    message: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.message


def _auth_base_url() -> str:
    base = (settings.SUPABASE_URL or "").rstrip("/")
    if not base:
        raise SupabaseAuthError("Supabase URL is not configured.", status_code=500)
    return f"{base}/auth/v1"


def _project_api_key() -> str:
    key = (settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_ROLE_KEY or "").strip()
    if not key:
        raise SupabaseAuthError("Supabase API key is not configured.", status_code=500)
    return key


def _request_json(method: str, path: str, *, payload: dict[str, Any] | None = None, access_token: str | None = None) -> dict[str, Any]:
    headers = {
        "apikey": _project_api_key(),
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    response = requests.request(
        method=method,
        url=f"{_auth_base_url()}{path}",
        json=payload,
        headers=headers,
        timeout=AUTH_TIMEOUT_SECONDS,
    )

    try:
        data = response.json()
    except ValueError:
        data = {"error_description": response.text or "Unexpected response from Supabase."}

    if response.status_code >= 400:
        message = (
            data.get("msg")
            or data.get("error_description")
            or data.get("error")
            or "Supabase authentication request failed."
        )
        raise SupabaseAuthError(str(message), status_code=response.status_code)

    if not isinstance(data, dict):
        raise SupabaseAuthError("Unexpected Supabase response format.", status_code=500)
    return data


def supabase_signup(*, email: str, password: str, metadata: dict[str, Any]) -> dict[str, Any]:
    """Create a Supabase-authenticated user."""
    payload = {
        "email": email.strip().lower(),
        "password": password,
        "data": metadata,
    }
    return _request_json("POST", "/signup", payload=payload)


def supabase_password_login(*, email: str, password: str) -> dict[str, Any]:
    """Authenticate against Supabase using email/password."""
    payload = {
        "email": email.strip().lower(),
        "password": password,
    }
    return _request_json("POST", "/token?grant_type=password", payload=payload)


def get_supabase_user(access_token: str) -> dict[str, Any]:
    """Resolve a Supabase user from an access token."""
    data = _request_json("GET", "/user", access_token=access_token)
    if not data.get("id"):
        raise SupabaseAuthError("Invalid access token.", status_code=401)
    return data


def _normalize_role(role: str | None) -> str:
    value = (role or "citizen").strip().lower()
    if value not in {"citizen", "authority", "admin"}:
        return "citizen"
    return value


def _resolve_or_create_user(email: str, full_name: str) -> User:
    existing = User.objects.filter(email__iexact=email).first()
    if existing:
        if existing.username != email:
            existing.username = email
        if full_name and existing.first_name != full_name:
            existing.first_name = full_name
        existing.save(update_fields=["username", "first_name"])
        return existing

    user = User(
        username=email,
        email=email,
        first_name=full_name,
        is_active=True,
    )
    user.set_unusable_password()
    user.save()
    return user


def _apply_profile_updates(profile: UserProfile, *, role: str, profile_data: dict[str, Any]) -> None:
    profile.role = role
    profile.city_corporation = (profile_data.get("city_corporation") or "").strip()

    ward_number = profile_data.get("ward_number")
    if ward_number in ("", None):
        profile.ward_number = None
    else:
        try:
            profile.ward_number = int(ward_number)
        except (TypeError, ValueError):
            profile.ward_number = None

    thana = (profile_data.get("thana") or "").strip()
    profile.thana = thana or None
    profile.department = (profile_data.get("department") or "").strip()
    profile.employee_id = (profile_data.get("employee_id") or "").strip()
    profile.phone_number = (profile_data.get("phone_number") or "").strip()
    profile.access_reason = (profile_data.get("access_reason") or "").strip()

    needs_approval = role in {"authority", "admin"}
    if needs_approval and profile.approval_status == "approved":
        profile.approval_status = "pending"
    elif not needs_approval:
        profile.approval_status = "approved"


def sync_local_user_from_supabase(
    supabase_user: dict[str, Any],
    *,
    role: str | None = None,
    profile_data: dict[str, Any] | None = None,
) -> User:
    """Mirror a Supabase-authenticated account into local relational records."""
    metadata = supabase_user.get("user_metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    email = (supabase_user.get("email") or metadata.get("email") or "").strip().lower()
    if not email:
        raise SupabaseAuthError("Supabase user email is missing.", status_code=400)

    full_name = (metadata.get("full_name") or metadata.get("name") or "").strip()
    merged_profile_data = {
        "city_corporation": metadata.get("city_corporation"),
        "ward_number": metadata.get("ward_number"),
        "thana": metadata.get("thana"),
        "department": metadata.get("department"),
        "employee_id": metadata.get("employee_id"),
        "phone_number": metadata.get("phone_number"),
        "access_reason": metadata.get("access_reason"),
    }
    if profile_data:
        merged_profile_data.update(profile_data)

    selected_role = _normalize_role(role or metadata.get("role"))

    with transaction.atomic():
        user = _resolve_or_create_user(email, full_name)

        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "role": selected_role,
                "approval_status": "approved" if selected_role == "citizen" else "pending",
            },
        )

        _apply_profile_updates(
            profile,
            role=selected_role,
            profile_data=merged_profile_data,
        )
        profile.save()

        user.is_active = profile.approval_status == "approved"
        user.save(update_fields=["is_active"])

    return user
