export const BACKEND_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export function backendUrl(path: string): string {
  if (!path) {
    return BACKEND_URL;
  }
  return `${BACKEND_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export function getCookieValue(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const cookie = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${name}=`));
  if (!cookie) {
    return null;
  }
  return decodeURIComponent(cookie.split("=")[1] || "");
}

export function getAccessToken(): string | null {
  return getCookieValue("dhaka_access_token");
}

export function clearAuthCookies(): void {
  ["dhaka_access_token", "dhaka_refresh_token", "dhaka_role", "dhaka_name", "dhaka_email"].forEach((name) => {
    document.cookie = `${name}=; Path=/; Max-Age=0; SameSite=Lax`;
  });
}

export function setAuthCookies(tokens: {
  accessToken?: string | null;
  refreshToken?: string | null;
  expiresIn?: number | null;
}): void {
  const safeExpires = Number(tokens.expiresIn || 3600);
  if (tokens.accessToken) {
    document.cookie = `dhaka_access_token=${encodeURIComponent(tokens.accessToken)}; Path=/; Max-Age=${safeExpires}; SameSite=Lax`;
  }
  if (tokens.refreshToken) {
    document.cookie = `dhaka_refresh_token=${encodeURIComponent(tokens.refreshToken)}; Path=/; Max-Age=2592000; SameSite=Lax`;
  }
}

export function setUserCookies(user: {
  role?: string;
  full_name?: string;
  email?: string;
}): void {
  const role = user.role || "citizen";
  document.cookie = `dhaka_role=${encodeURIComponent(role)}; Path=/; Max-Age=2592000; SameSite=Lax`;
  if (user.full_name) {
    document.cookie = `dhaka_name=${encodeURIComponent(user.full_name)}; Path=/; Max-Age=2592000; SameSite=Lax`;
  }
  if (user.email) {
    document.cookie = `dhaka_email=${encodeURIComponent(user.email)}; Path=/; Max-Age=2592000; SameSite=Lax`;
  }
}

export async function postJson<T>(path: string, payload: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(backendUrl(path), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error(`Cannot reach backend at ${BACKEND_URL}. Check backend server status and CORS/host settings.`);
  }

  const data = (await response.json()) as T & { success?: boolean; error?: string };
  if (!response.ok || (typeof data === "object" && data && "success" in data && data.success === false)) {
    throw new Error((data as { error?: string }).error || "Request failed.");
  }
  return data as T;
}

async function parseApiResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  const data = text ? (JSON.parse(text) as T & { success?: boolean; error?: string }) : ({} as T & { success?: boolean; error?: string });

  if (!response.ok || (typeof data === "object" && data && "success" in data && data.success === false)) {
    throw new Error((data as { error?: string }).error || "Request failed.");
  }
  return data as T;
}

function buildAuthHeaders(headers?: HeadersInit): Headers {
  const merged = new Headers(headers || {});
  const token = getAccessToken();
  if (token) {
    merged.set("Authorization", `Bearer ${token}`);
  }
  return merged;
}

export async function authGetJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(backendUrl(path), {
      method: "GET",
      headers: buildAuthHeaders(),
      credentials: "include",
    });
  } catch {
    throw new Error(`Cannot reach backend at ${BACKEND_URL}. Check backend server status and CORS/host settings.`);
  }
  return parseApiResponse<T>(response);
}

export async function authPostJson<T>(path: string, payload: unknown): Promise<T> {
  const headers = buildAuthHeaders({ "Content-Type": "application/json" });
  let response: Response;
  try {
    response = await fetch(backendUrl(path), {
      method: "POST",
      headers,
      credentials: "include",
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error(`Cannot reach backend at ${BACKEND_URL}. Check backend server status and CORS/host settings.`);
  }
  return parseApiResponse<T>(response);
}

export async function authPostForm<T>(path: string, formData: FormData): Promise<T> {
  let response: Response;
  try {
    response = await fetch(backendUrl(path), {
      method: "POST",
      headers: buildAuthHeaders(),
      credentials: "include",
      body: formData,
    });
  } catch {
    throw new Error(`Cannot reach backend at ${BACKEND_URL}. Check backend server status and CORS/host settings.`);
  }
  return parseApiResponse<T>(response);
}

export async function establishBackendSession(accessToken: string): Promise<void> {
  const response = await fetch(backendUrl("/api/auth/session/"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    credentials: "include",
    body: JSON.stringify({}),
  });

  const data = (await response.json()) as { success?: boolean; error?: string };
  if (!response.ok || data.success === false) {
    throw new Error(data.error || "Unable to establish backend session.");
  }
}

export async function destroyBackendSession(): Promise<void> {
  await fetch(backendUrl("/api/auth/session/logout/"), {
    method: "POST",
    credentials: "include",
  });
}
