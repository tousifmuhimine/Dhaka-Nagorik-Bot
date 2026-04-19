"""Authentication decorators that accept Django sessions or Supabase bearer tokens."""

from __future__ import annotations

from functools import wraps

from django.http import JsonResponse

from .supabase_auth import SupabaseAuthError, get_supabase_user, sync_local_user_from_supabase


def login_or_bearer_required(view_func):
    """Allow requests from either Django session auth or Supabase bearer auth."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        session_user = getattr(request, "user", None)
        if session_user and session_user.is_authenticated:
            return view_func(request, *args, **kwargs)

        authorization = (request.headers.get("Authorization") or "").strip()
        if not authorization.startswith("Bearer "):
            return JsonResponse(
                {"success": False, "error": "Missing bearer token."},
                status=401,
            )

        token = authorization.split(" ", 1)[1].strip()
        if not token:
            return JsonResponse(
                {"success": False, "error": "Bearer token is empty."},
                status=401,
            )

        try:
            supabase_user = get_supabase_user(token)
            request.user = sync_local_user_from_supabase(supabase_user)
            request.supabase_user = supabase_user
        except SupabaseAuthError as exc:
            return JsonResponse(
                {"success": False, "error": str(exc)},
                status=exc.status_code,
            )

        return view_func(request, *args, **kwargs)

    return _wrapped
