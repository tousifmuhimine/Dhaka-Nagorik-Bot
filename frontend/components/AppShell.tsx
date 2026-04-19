"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { clearAuthCookies, destroyBackendSession, getCookieValue } from "@/lib/backend";
import type { UserRole } from "@/lib/types";

type AppShellProps = {
  role: UserRole;
  title: string;
  subtitle?: string;
  hidePageHeader?: boolean;
  mainClassName?: string;
  children: ReactNode;
};

export default function AppShell({
  role,
  title,
  subtitle,
  hidePageHeader = false,
  mainClassName,
  children,
}: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const fullName = getCookieValue("dhaka_name") || "User";
  const roleLabel = role.charAt(0).toUpperCase() + role.slice(1);

  const links: Array<{ href: string; label: string }> = [];
  if (role === "citizen") {
    links.push({ href: "/citizen", label: "Dashboard" });
    links.push({ href: "/chatbot", label: "Complaint Assistant" });
  }
  if (role === "authority") {
    links.push({ href: "/authority", label: "Manage Complaints" });
  }
  if (role === "admin") {
    links.push({ href: "/dashboard/admin", label: "Admin Panel" });
  }

  async function handleLogout() {
    try {
      await destroyBackendSession();
    } catch {
      // Ignore network errors while clearing local auth state.
    }
    clearAuthCookies();
    router.replace("/login");
  }

  return (
    <div className="min-h-screen">
      <header className="app-nav sticky top-0 z-30">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3">
          <div className="app-title-font text-xl font-bold text-white">Dhaka Nagorik AI</div>
          <div className="flex items-center gap-3">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`app-link rounded-lg px-2 py-1 text-sm ${pathname === link.href ? "bg-white/10" : ""}`}
              >
                {link.label}
              </Link>
            ))}
            <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-right leading-tight">
              <div className="text-xs font-semibold text-white/90">{fullName}</div>
              <div className="text-[0.68rem] uppercase tracking-[0.12em] text-white/60">{roleLabel}</div>
            </div>
            <button type="button" className="app-theme-toggle" data-theme-toggle>
              <span data-theme-label>Bright Mode</span>
            </button>
            <button type="button" className="app-btn app-btn-danger text-sm" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className={mainClassName || "mx-auto w-full max-w-7xl px-4 py-8"}>
        {!hidePageHeader ? (
          <div className="mb-6">
            <h1 className="app-panel-title text-3xl">{title}</h1>
            {subtitle ? <p className="app-muted mt-2 text-sm">{subtitle}</p> : null}
          </div>
        ) : null}
        {children}
      </main>
    </div>
  );
}
