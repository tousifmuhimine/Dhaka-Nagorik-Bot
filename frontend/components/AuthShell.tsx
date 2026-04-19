import Link from "next/link";
import type { ReactNode } from "react";

type AuthShellProps = {
  mode: "login" | "signup";
  onModeChange?: (mode: "login" | "signup") => void;
  badge: string;
  heading: string;
  description: string;
  notice?: { type: "error" | "success" | "warning"; message: string } | null;
  children: ReactNode;
};

export default function AuthShell({
  mode,
  onModeChange,
  badge,
  heading,
  description,
  notice,
  children,
}: AuthShellProps) {
  return (
    <div className="relative min-h-screen overflow-hidden px-5 py-6 sm:px-8 sm:py-8 lg:px-12">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-[-12rem] top-[-8rem] h-[28rem] w-[28rem] rounded-full bg-emerald-300/10 blur-3xl" />
        <div className="absolute bottom-[-10rem] right-[-6rem] h-[24rem] w-[24rem] rounded-full bg-amber-200/10 blur-3xl" />
      </div>

      <div className="relative z-20 mx-auto flex max-w-6xl justify-end">
        <button type="button" className="app-theme-toggle" data-theme-toggle>
          <span data-theme-label>Bright Mode</span>
        </button>
      </div>

      <div className="intro-brand px-6 text-center">
        <div className="intro-brand__inner">
          <div className="intro-brand__kicker">Citizen Support Experience</div>
          <h1 className="intro-brand__title auth-title-font">Dhaka Nagorik AI</h1>
          <p className="intro-brand__subtitle text-sm sm:text-base">
            Smart civic access for Dhaka residents, with a cleaner sign in flow and a modern complaint experience.
          </p>
        </div>
      </div>

      <div className="relative mx-auto flex min-h-[calc(100vh-3rem)] max-w-6xl items-center justify-center lg:min-h-[calc(100vh-4rem)]">
        <div className="auth-content grid w-full gap-8 lg:grid-cols-[1.08fr_0.92fr] lg:items-center">
          <section className="pt-28 lg:pt-24">
            <div className="mb-6 inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-[0.68rem] uppercase tracking-[0.36em] text-white/70">
              Built for Dhaka residents
            </div>
            <div className="max-w-xl space-y-5">
              <h2 className="auth-title-font text-4xl font-bold leading-tight text-white sm:text-5xl">
                Complaint support that feels calm, fast, and clear.
              </h2>
              <p className="text-base leading-7 text-white/70 sm:text-lg">
                Start with a secure account, speak to the assistant, and track important civic issues without getting lost in a clunky interface.
              </p>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              <div className="auth-metric-card rounded-3xl p-5">
                <div className="mb-3 text-sm text-emerald-200">24/7</div>
                <div className="text-lg font-semibold text-white">Guided Access</div>
                <p className="mt-2 text-sm leading-6 text-white/60">Login and report issues through one clear starting point.</p>
              </div>
              <div className="auth-metric-card rounded-3xl p-5">
                <div className="mb-3 text-sm text-amber-100">AI</div>
                <div className="text-lg font-semibold text-white">Smart Intake</div>
                <p className="mt-2 text-sm leading-6 text-white/60">The experience is designed around assisted complaint handling.</p>
              </div>
              <div className="auth-metric-card rounded-3xl p-5">
                <div className="mb-3 text-sm text-cyan-100">Safe</div>
                <div className="text-lg font-semibold text-white">Secure Entry</div>
                <p className="mt-2 text-sm leading-6 text-white/60">Simple sign up and login with a more polished first impression.</p>
              </div>
            </div>
          </section>

          <section className="auth-shell rounded-[2rem] p-4 sm:p-6">
            <div className="relative z-10 rounded-[1.6rem] border border-white/10 bg-black/40 p-6 sm:p-8">
              <div className="mb-6 flex rounded-2xl bg-white/[0.04] p-1.5">
                {onModeChange ? (
                  <>
                    <button
                      type="button"
                      className={`auth-tab ${mode === "login" ? "is-active" : ""} flex-1 rounded-2xl px-4 py-3 text-center text-sm font-semibold`}
                      onClick={() => onModeChange("login")}
                    >
                      Login
                    </button>
                    <button
                      type="button"
                      className={`auth-tab ${mode === "signup" ? "is-active" : ""} flex-1 rounded-2xl px-4 py-3 text-center text-sm font-semibold`}
                      onClick={() => onModeChange("signup")}
                    >
                      Sign Up
                    </button>
                  </>
                ) : (
                  <>
                    <Link
                      href="/login"
                      className={`auth-tab ${mode === "login" ? "is-active" : ""} flex-1 rounded-2xl px-4 py-3 text-center text-sm font-semibold`}
                    >
                      Login
                    </Link>
                    <Link
                      href="/signup"
                      className={`auth-tab ${mode === "signup" ? "is-active" : ""} flex-1 rounded-2xl px-4 py-3 text-center text-sm font-semibold`}
                    >
                      Sign Up
                    </Link>
                  </>
                )}
              </div>

              <div className="mb-8">
                <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs uppercase tracking-[0.3em] text-white/60">
                  {badge}
                </div>
                <h3 className="text-3xl font-bold text-white">{heading}</h3>
                <p className="mt-3 text-sm leading-6 text-white/70">{description}</p>
              </div>

              {notice && (
                <div className="mb-6 space-y-3">
                  <div
                    className={`rounded-2xl border px-4 py-3 text-sm ${
                      notice.type === "error"
                        ? "border-red-400/25 bg-red-400/10 text-red-100"
                        : notice.type === "success"
                          ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-100"
                          : "border-amber-300/25 bg-amber-300/10 text-amber-50"
                    }`}
                  >
                    {notice.message}
                  </div>
                </div>
              )}

              {children}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
