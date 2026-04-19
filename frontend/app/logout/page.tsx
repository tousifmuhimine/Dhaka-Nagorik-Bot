"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { clearAuthCookies, destroyBackendSession } from "@/lib/backend";

export default function LogoutPage() {
  const router = useRouter();

  useEffect(() => {
    async function signOut() {
      try {
        await destroyBackendSession();
      } catch {
        // Ignore cleanup errors.
      }

      clearAuthCookies();
      router.replace("/login");
    }

    void signOut();
  }, [router]);

  return null;
}
