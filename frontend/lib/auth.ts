"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { clearAuthCookies, getAccessToken, getCookieValue } from "@/lib/backend";
import type { UserRole } from "@/lib/types";

export function useRoleGuard(allowedRoles: UserRole[]) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [role, setRole] = useState<UserRole | null>(null);

  const allowed = useMemo(() => new Set(allowedRoles), [allowedRoles]);

  useEffect(() => {
    const token = getAccessToken();
    const cookieRole = getCookieValue("dhaka_role") as UserRole | null;

    if (!token || !cookieRole || !allowed.has(cookieRole)) {
      clearAuthCookies();
      router.replace("/login");
      return;
    }

    setRole(cookieRole);
    setReady(true);
  }, [allowed, router]);

  return { ready, role };
}
