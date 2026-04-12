from dataclasses import dataclass

from fastapi import Header, HTTPException


@dataclass(slots=True)
class UserContext:
    user_id: str
    role: str
    assigned_thana: str | None = None


async def get_user_context(
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
    x_user_thana: str | None = Header(default=None),
) -> UserContext:
    # This lightweight dependency keeps the scaffold runnable. In production,
    # swap it for Supabase JWT verification and role resolution.
    if not x_user_id or not x_user_role:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication headers. Provide X-User-Id and X-User-Role.",
        )
    return UserContext(user_id=x_user_id, role=x_user_role.lower(), assigned_thana=x_user_thana)
