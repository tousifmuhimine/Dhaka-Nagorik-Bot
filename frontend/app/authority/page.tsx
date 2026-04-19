"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { useRoleGuard } from "@/lib/auth";
import { authGetJson, authPostJson } from "@/lib/backend";

type UserBrief = {
  id: number;
  email: string;
  full_name: string;
  username: string;
};

type ComplaintItem = {
  id: number;
  category_display: string;
  area: string;
  service_area: string;
  status: string;
  status_display: string;
  created_at: string;
  acknowledged_at: string | null;
  citizen: UserBrief | null;
  assigned_authority: UserBrief | null;
};

type AuthorityDashboardResponse = {
  success: boolean;
  service_area: string;
  stats: {
    total: number;
    pending: number;
    awaiting_confirmation: number;
    assigned_count: number;
  };
  complaints: ComplaintItem[];
};

function badgeClass(status: string) {
  if (status === "resolved") {
    return "app-status-resolved";
  }
  if (status === "awaiting_citizen_confirmation") {
    return "app-status-waiting";
  }
  if (status === "acknowledged" || status === "in_progress" || status === "under_review") {
    return "app-status-active";
  }
  return "app-status-default";
}

export default function AuthorityPage() {
  const { ready, role } = useRoleGuard(["authority"]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [serviceArea, setServiceArea] = useState("");
  const [stats, setStats] = useState({ total: 0, pending: 0, awaiting_confirmation: 0, assigned_count: 0 });
  const [complaints, setComplaints] = useState<ComplaintItem[]>([]);

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    try {
      const data = await authGetJson<AuthorityDashboardResponse>("/api/dashboard/authority/");
      setServiceArea(data.service_area);
      setStats(data.stats);
      setComplaints(data.complaints);
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Failed to load authority dashboard.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  async function acknowledgeComplaint(id: number) {
    setNotice(null);
    setError(null);
    try {
      const data = await authPostJson<{ success: boolean; message: string }>(`/api/complaints/${id}/acknowledge/`, {});
      setNotice(data.message);
      await loadDashboard();
    } catch (actionError) {
      const message = actionError instanceof Error ? actionError.message : "Failed to acknowledge complaint.";
      setError(message);
    }
  }

  async function requestResolution(id: number) {
    setNotice(null);
    setError(null);
    try {
      const data = await authPostJson<{ success: boolean; message: string }>(`/api/complaints/${id}/request-resolution/`, {});
      setNotice(data.message);
      await loadDashboard();
    } catch (actionError) {
      const message = actionError instanceof Error ? actionError.message : "Failed to mark complaint as solved.";
      setError(message);
    }
  }

  useEffect(() => {
    if (!ready || role !== "authority") {
      return;
    }
    void loadDashboard();
  }, [ready, role]);

  if (!ready || role !== "authority") {
    return null;
  }

  return (
    <AppShell
      role="authority"
      title="Authority Dashboard"
      subtitle="Manage area-assigned complaints and submit resolution requests for citizen confirmation."
    >
      <div className="grid gap-4 mb-8 md:grid-cols-4">
        <div className="app-surface rounded-3xl p-6">
          <div className="app-kicker">Service Area</div>
          <div className="mt-3 text-2xl font-bold text-white">{serviceArea || "Not set"}</div>
        </div>
        <div className="app-surface rounded-3xl p-6">
          <div className="app-kicker">Total Complaints</div>
          <div className="mt-3 text-3xl font-bold text-white">{stats.total}</div>
        </div>
        <div className="app-surface rounded-3xl p-6">
          <div className="app-kicker">Assigned to You</div>
          <div className="mt-3 text-3xl font-bold text-emerald-200">{stats.assigned_count}</div>
        </div>
        <div className="app-surface rounded-3xl p-6">
          <div className="app-kicker">Awaiting Citizen Confirmation</div>
          <div className="mt-3 text-3xl font-bold text-amber-100">{stats.awaiting_confirmation}</div>
        </div>
      </div>

      {error ? <div className="app-surface mb-4 rounded-2xl border border-red-400/30 bg-red-500/10 p-4 text-red-100">{error}</div> : null}
      {notice ? <div className="app-surface mb-4 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-4 text-emerald-100">{notice}</div> : null}

      <div className="app-surface rounded-[2rem] p-8">
        <div className="mb-6">
          <h2 className="app-panel-title text-2xl">Complaints in {serviceArea || "your area"}</h2>
          <p className="text-sm app-muted mt-1">You can acknowledge and resolve complaints from your assigned ward coverage.</p>
        </div>

        {loading ? (
          <p className="app-empty rounded-2xl px-6 py-8 text-center">Loading complaints...</p>
        ) : complaints.length ? (
          <div className="overflow-x-auto">
            <table className="app-table text-sm">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left font-medium">ID</th>
                  <th className="px-4 py-3 text-left font-medium">Citizen</th>
                  <th className="px-4 py-3 text-left font-medium">Category</th>
                  <th className="px-4 py-3 text-left font-medium">Area</th>
                  <th className="px-4 py-3 text-left font-medium">Status</th>
                  <th className="px-4 py-3 text-left font-medium">Filed</th>
                  <th className="px-4 py-3 text-left font-medium">Acknowledged</th>
                  <th className="px-4 py-3 text-left font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {complaints.map((complaint) => {
                  const canAcknowledge = complaint.status === "submitted";
                  const canMarkSolved = complaint.status === "acknowledged";

                  return (
                    <tr key={complaint.id} className="align-top">
                      <td className="px-4 py-3">#{complaint.id}</td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-white">{complaint.citizen?.full_name || "Citizen"}</div>
                        <div className="text-xs app-dim">{complaint.citizen?.email || ""}</div>
                      </td>
                      <td className="px-4 py-3">{complaint.category_display}</td>
                      <td className="px-4 py-3">
                        <div className="text-white">{complaint.area}</div>
                        <div className="text-xs app-dim">{complaint.service_area}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`app-status rounded-full px-2 py-1 text-xs font-medium ${badgeClass(complaint.status)}`}>
                          {complaint.status_display}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs app-dim">{new Date(complaint.created_at).toLocaleString()}</td>
                      <td className="px-4 py-3 text-xs app-dim">{complaint.acknowledged_at ? new Date(complaint.acknowledged_at).toLocaleString() : "Not yet"}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col items-start gap-2">
                          <Link href={`/complaint/${complaint.id}`} className="app-link">
                            View details
                          </Link>
                          {canAcknowledge ? (
                            <button type="button" className="app-btn app-btn-secondary px-3 py-2 text-xs" onClick={() => acknowledgeComplaint(complaint.id)}>
                              Acknowledge
                            </button>
                          ) : null}
                          {canMarkSolved ? (
                            <button type="button" className="app-btn app-btn-success px-3 py-2 text-xs" onClick={() => requestResolution(complaint.id)}>
                              Mark as Solved
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="app-empty rounded-2xl px-6 py-8 text-center">No complaints in this assigned service area.</p>
        )}
      </div>
    </AppShell>
  );
}
