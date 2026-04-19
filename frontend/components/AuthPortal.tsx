"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import AuthShell from "@/components/AuthShell";
import { establishBackendSession, postJson, setAuthCookies, setUserCookies } from "@/lib/backend";
import type { LoginResponse, SignupResponse, UserRole } from "@/lib/types";

type AuthMode = "login" | "signup";

type NoticeState = {
  type: "error" | "success" | "warning";
  message: string;
};

type SignupFormState = {
  role: UserRole;
  full_name: string;
  city_corporation: string;
  ward_number: string;
  thana: string;
  department: string;
  employee_id: string;
  phone_number: string;
  access_reason: string;
  email: string;
  password: string;
  confirm_password: string;
};

const initialSignupState: SignupFormState = {
  role: "citizen",
  full_name: "",
  city_corporation: "",
  ward_number: "",
  thana: "",
  department: "",
  employee_id: "",
  phone_number: "",
  access_reason: "",
  email: "",
  password: "",
  confirm_password: "",
};

const wardOptions = Array.from({ length: 75 }, (_, index) => index + 1);

function routeForRole(role: string): string {
  if (role === "authority") {
    return "/authority";
  }
  if (role === "admin") {
    return "/dashboard/admin";
  }
  return "/citizen";
}

function replaceUrlForMode(mode: AuthMode, signupStatus?: "success" | "pending" | null) {
  if (typeof window === "undefined") {
    return;
  }

  const url = new URL(window.location.href);
  url.pathname = mode === "signup" ? "/signup" : "/login";

  if (signupStatus) {
    url.searchParams.set("signup", signupStatus);
  } else {
    url.searchParams.delete("signup");
  }

  window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}`);
}

export default function AuthPortal({ initialMode }: { initialMode: AuthMode }) {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [notice, setNotice] = useState<NoticeState | null>(null);

  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  const [signupForm, setSignupForm] = useState<SignupFormState>(initialSignupState);
  const [signupLoading, setSignupLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const signupStatus = params.get("signup");

    if (signupStatus === "success") {
      setMode("login");
      setNotice({ type: "success", message: "Account created successfully. Please log in." });
      replaceUrlForMode("login", "success");
      return;
    }

    if (signupStatus === "pending") {
      setMode("login");
      setNotice({ type: "warning", message: "Registration submitted. Admin approval is required before login." });
      replaceUrlForMode("login", "pending");
      return;
    }

    replaceUrlForMode(initialMode, null);
  }, [initialMode]);

  const authMeta = useMemo(() => {
    if (mode === "signup") {
      return {
        badge: "New Account",
        heading: "Create your access",
        description:
          "Citizens can start right away. Authority and admin registrations include extra verification details and stay pending until an approved admin reviews them.",
      };
    }

    return {
      badge: "Returning User",
      heading: "Welcome back",
      description:
        "Citizens, approved authorities, and approved admins can log in here to continue with complaint tracking and civic workflow actions.",
    };
  }, [mode]);

  const showAuthorityFields = signupForm.role === "authority";
  const showElevatedFields = signupForm.role === "authority" || signupForm.role === "admin";

  const passwordMismatch = useMemo(
    () => signupForm.confirm_password.length > 0 && signupForm.password !== signupForm.confirm_password,
    [signupForm.confirm_password, signupForm.password],
  );

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode);
    setNotice(null);
    replaceUrlForMode(nextMode, null);
  }

  async function handleLoginSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loginLoading) {
      return;
    }

    setNotice(null);
    setLoginLoading(true);

    try {
      const data = await postJson<LoginResponse>("/api/auth/login/", {
        email: loginEmail,
        password: loginPassword,
      });

      setAuthCookies({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        expiresIn: data.expires_in,
      });
      setUserCookies(data.user);
      await establishBackendSession(data.access_token);
      router.push(routeForRole(data.user.role));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Login failed.";
      setNotice({ type: "error", message });
    } finally {
      setLoginLoading(false);
    }
  }

  function updateSignupField<K extends keyof SignupFormState>(key: K, value: SignupFormState[K]) {
    setSignupForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSignupSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (signupLoading) {
      return;
    }

    if (signupForm.password !== signupForm.confirm_password) {
      setNotice({ type: "error", message: "Password and confirm password must match." });
      return;
    }

    setNotice(null);
    setSignupLoading(true);

    try {
      const payload = {
        role: signupForm.role,
        full_name: signupForm.full_name,
        city_corporation: signupForm.role === "authority" ? signupForm.city_corporation : "",
        ward_number: signupForm.role === "authority" && signupForm.ward_number ? Number(signupForm.ward_number) : null,
        thana: signupForm.role === "authority" ? signupForm.thana : "",
        department: showElevatedFields ? signupForm.department : "",
        employee_id: showElevatedFields ? signupForm.employee_id : "",
        phone_number: showElevatedFields ? signupForm.phone_number : "",
        access_reason: showElevatedFields ? signupForm.access_reason : "",
        email: signupForm.email,
        password: signupForm.password,
      };

      const response = await postJson<SignupResponse>("/api/auth/signup/", payload);

      const signupStatus = response.user.role === "citizen" ? "success" : "pending";
      const signupMessage =
        signupStatus === "success"
          ? "Account created successfully. Please log in."
          : "Registration submitted. Admin approval is required before login.";

      setLoginEmail(signupForm.email);
      setLoginPassword("");
      setSignupForm(initialSignupState);
      setMode("login");
      setNotice({ type: signupStatus === "success" ? "success" : "warning", message: signupMessage });
      replaceUrlForMode("login", signupStatus);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Signup failed.";
      setNotice({ type: "error", message });
    } finally {
      setSignupLoading(false);
    }
  }

  return (
    <AuthShell
      mode={mode}
      onModeChange={switchMode}
      badge={authMeta.badge}
      heading={authMeta.heading}
      description={authMeta.description}
      notice={notice}
    >
      <div className={`auth-carousel ${mode === "signup" ? "is-signup" : "is-login"}`}>
        <div className="auth-carousel-track">
          <section className="auth-pane" aria-hidden={mode !== "login"}>
            <form onSubmit={handleLoginSubmit} className="space-y-5">
              <div>
                <label className="mb-2 block text-sm font-medium text-white/80">Email</label>
                <input
                  type="email"
                  className="auth-input"
                  placeholder="Enter your email"
                  autoComplete="email"
                  autoFocus={mode === "login"}
                  value={loginEmail}
                  onChange={(event) => setLoginEmail(event.target.value)}
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-white/80">Password</label>
                <input
                  type="password"
                  className="auth-input"
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  value={loginPassword}
                  onChange={(event) => setLoginPassword(event.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                className="auth-submit mt-2 w-full rounded-2xl px-4 py-4 text-sm font-bold uppercase tracking-[0.2em] transition"
                disabled={loginLoading}
              >
                {loginLoading ? "Logging in..." : "Login"}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-white/55">
              Need an account?{" "}
              <button
                type="button"
                className="font-semibold text-emerald-200 transition hover:text-white"
                onClick={() => switchMode("signup")}
              >
                Create one now
              </button>
            </p>

            <p className="mt-3 text-center text-xs leading-5 text-white/40">
              Authority and admin signups stay locked until an approved admin reviews the request.
            </p>
          </section>

          <section className="auth-pane" aria-hidden={mode !== "signup"}>
            <form onSubmit={handleSignupSubmit} className="space-y-5">
              <div>
                <label className="mb-2 block text-sm font-medium text-white/80">Account Type</label>
                <select
                  className="auth-input"
                  value={signupForm.role}
                  onChange={(event) => updateSignupField("role", event.target.value as UserRole)}
                >
                  <option value="citizen">Citizen</option>
                  <option value="authority">Authority</option>
                  <option value="admin">Admin</option>
                </select>
                <p className="mt-2 text-xs leading-5 text-white/45">
                  Choose citizen for direct access, or request authority/admin access for reviewed accounts.
                </p>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-white/80">Full Name</label>
                <input
                  type="text"
                  className="auth-input"
                  placeholder="Your full name"
                  autoComplete="name"
                  autoFocus={mode === "signup"}
                  value={signupForm.full_name}
                  onChange={(event) => updateSignupField("full_name", event.target.value)}
                  required
                />
              </div>

              {showAuthorityFields ? (
                <>
                  <div>
                    <label className="mb-2 block text-sm font-medium text-white/80">City Corporation</label>
                    <select
                      className="auth-input"
                      value={signupForm.city_corporation}
                      onChange={(event) => updateSignupField("city_corporation", event.target.value)}
                      required
                    >
                      <option value="">Select city corporation</option>
                      <option value="DNCC">DNCC</option>
                      <option value="DSCC">DSCC</option>
                    </select>
                    <p className="mt-2 text-xs leading-5 text-white/45">
                      Use the official city corporation that owns the ward you serve.
                    </p>
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-white/80">Ward Number</label>
                    <select
                      className="auth-input"
                      value={signupForm.ward_number}
                      onChange={(event) => updateSignupField("ward_number", event.target.value)}
                      required
                    >
                      <option value="">Select ward</option>
                      {wardOptions.map((ward) => (
                        <option key={ward} value={ward}>
                          {ward}
                        </option>
                      ))}
                    </select>
                    <p className="mt-2 text-xs leading-5 text-white/45">
                      Only one approved authority can own a specific ward at a time.
                    </p>
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-white/80">Neighborhood Label</label>
                    <input
                      type="text"
                      className="auth-input"
                      placeholder="Neighborhood label (e.g. Dhanmondi, Gulshan)"
                      value={signupForm.thana}
                      onChange={(event) => updateSignupField("thana", event.target.value)}
                      required
                    />
                    <p className="mt-2 text-xs leading-5 text-white/45">
                      This keeps the service area recognizable for admins and citizens, for example Dhanmondi or Gulshan.
                    </p>
                  </div>
                </>
              ) : null}

              {showElevatedFields ? (
                <>
                  <div>
                    <label className="mb-2 block text-sm font-medium text-white/80">Department / Office</label>
                    <input
                      type="text"
                      className="auth-input"
                      placeholder="Department or office name"
                      value={signupForm.department}
                      onChange={(event) => updateSignupField("department", event.target.value)}
                      required
                    />
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-white/80">Employee / Government ID</label>
                    <input
                      type="text"
                      className="auth-input"
                      placeholder="Employee ID or government ID"
                      value={signupForm.employee_id}
                      onChange={(event) => updateSignupField("employee_id", event.target.value)}
                      required
                    />
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-white/80">Phone Number</label>
                    <input
                      type="text"
                      className="auth-input"
                      placeholder="Contact phone number"
                      autoComplete="tel"
                      value={signupForm.phone_number}
                      onChange={(event) => updateSignupField("phone_number", event.target.value)}
                      required
                    />
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-white/80">Access Reason</label>
                    <textarea
                      className="auth-input min-h-28"
                      placeholder="Tell the admin why you need this access and what area you serve."
                      rows={4}
                      value={signupForm.access_reason}
                      onChange={(event) => updateSignupField("access_reason", event.target.value)}
                      required
                    />
                    <p className="mt-2 text-xs leading-5 text-white/45">
                      Briefly explain your civic responsibility, office, and why this access should be approved.
                    </p>
                  </div>
                </>
              ) : null}

              <div>
                <label className="mb-2 block text-sm font-medium text-white/80">Email</label>
                <input
                  type="email"
                  className="auth-input"
                  placeholder="you@example.com"
                  autoComplete="email"
                  value={signupForm.email}
                  onChange={(event) => updateSignupField("email", event.target.value)}
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-white/80">Password</label>
                <input
                  type="password"
                  className="auth-input"
                  placeholder="Create a password"
                  autoComplete="new-password"
                  value={signupForm.password}
                  onChange={(event) => updateSignupField("password", event.target.value)}
                  required
                />
                <p className="mt-2 text-xs leading-5 text-white/45">Use at least 8 characters for a stronger account.</p>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-white/80">Confirm Password</label>
                <input
                  type="password"
                  className="auth-input"
                  placeholder="Confirm your password"
                  autoComplete="new-password"
                  value={signupForm.confirm_password}
                  onChange={(event) => updateSignupField("confirm_password", event.target.value)}
                  required
                />
                {passwordMismatch ? (
                  <p className="mt-2 text-sm text-red-200">Password confirmation does not match.</p>
                ) : null}
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-xs leading-6 text-white/55">
                Authority and admin accounts cannot log in until an approved admin confirms the request.
              </div>

              <button
                type="submit"
                className="auth-submit mt-2 w-full rounded-2xl px-4 py-4 text-sm font-bold uppercase tracking-[0.2em] transition"
                disabled={signupLoading}
              >
                {signupLoading ? "Creating..." : "Create Account"}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-white/55">
              Already registered?{" "}
              <button
                type="button"
                className="font-semibold text-amber-100 transition hover:text-white"
                onClick={() => switchMode("login")}
              >
                Login here
              </button>
            </p>
          </section>
        </div>
      </div>
    </AuthShell>
  );
}
