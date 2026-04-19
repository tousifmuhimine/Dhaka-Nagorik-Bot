"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

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
  description: string;
  status: string;
  status_display: string;
  created_at: string;
  acknowledged_at: string | null;
  resolution_requested_at: string | null;
  citizen_confirmed_at: string | null;
  last_reminder_sent_at: string | null;
  citizen: UserBrief | null;
  assigned_authority: UserBrief | null;
};

type AccessRequest = {
  id: number;
  role: string;
  service_area: string;
  department: string;
  employee_id: string;
  phone_number: string;
  access_reason: string;
  created_at: string;
  user: UserBrief | null;
};

type StatusChoice = {
  value: string;
  label: string;
};

type AdminDashboardResponse = {
  success: boolean;
  stats: {
    total_complaints: number;
    total_users: number;
    resolved: number;
    pending: number;
    awaiting_confirmation: number;
  };
  search: string;
  status: string;
  status_choices: StatusChoice[];
  complaints: ComplaintItem[];
  pending_requests: AccessRequest[];
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

export default function AdminDashboardPage() {
  const { ready, role } = useRoleGuard(["admin"]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [stats, setStats] = useState({
    total_complaints: 0,
    total_users: 0,
    resolved: 0,
    pending: 0,
    awaiting_confirmation: 0,
  });
  const [complaints, setComplaints] = useState<ComplaintItem[]>([]);
  const [pendingRequests, setPendingRequests] = useState<AccessRequest[]>([]);
  const [statusChoices, setStatusChoices] = useState<StatusChoice[]>([]);

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    if (search.trim()) {
      params.set("search", search.trim());
    }
    if (status) {
      params.set("status", status);
    }
    const query = params.toString();
    return query ? `?${query}` : "";
  }, [search, status]);

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    try {
      const data = await authGetJson<AdminDashboardResponse>(`/api/dashboard/admin/${queryString}`);
      setStats(data.stats);
      setComplaints(data.complaints);
      setPendingRequests(data.pending_requests);
      setStatusChoices(data.status_choices);
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Failed to load admin dashboard.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!ready || role !== "admin") {
      return;
    }
    void loadDashboard();
  }, [ready, role, queryString]);

  async function approve(profileId: number) {
    setNotice(null);
    setError(null);
    try {
      const response = await authPostJson<{ success: boolean; message: string }>(`/api/dashboard/admin/access-request/${profileId}/approve/`, {});
      setNotice(response.message);
      await loadDashboard();
    } catch (actionError) {
      const message = actionError instanceof Error ? actionError.message : "Failed to approve access request.";
      setError(message);
    }
  }

  async function reject(profileId: number) {
    setNotice(null);
    setError(null);
    try {
      const response = await authPostJson<{ success: boolean; message: string }>(`/api/dashboard/admin/access-request/${profileId}/reject/`, {});
      setNotice(response.message);
      await loadDashboard();
    } catch (actionError) {
      const message = actionError instanceof Error ? actionError.message : "Failed to reject access request.";
      setError(message);
    }
  }

  async function remind(complaintId: number) {
    setNotice(null);
    setError(null);
    try {
      const response = await authPostJson<{ success: boolean; message: string }>(`/api/dashboard/admin/complaint/${complaintId}/remind/`, {});
      setNotice(response.message);
      await loadDashboard();
    } catch (actionError) {
      const message = actionError instanceof Error ? actionError.message : "Failed to send reminder.";
      setError(message);
    }
  }

  function onFilterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void loadDashboard();
  }

  if (!ready || role !== "admin") {
    return null;
  }

  return (
    <AppShell
      role="admin"
      title="Admin Dashboard"
      subtitle="Review access requests, monitor all complaints, and send reminders to assigned authorities."
    >
      <div className="grid gap-4 mb-8 md:grid-cols-2 xl:grid-cols-5">
        <div className="app-surface rounded-3xl p-6">
          <div className="app-kicker">Total Complaints</div>
          <div className="mt-3 text-3xl font-bold text-white">{stats.total_complaints}</div>
        </div>
        <div className="app-surface rounded-3xl p-6">
          <div className="app-kicker">Resolved</div>
          <div className="mt-3 text-3xl font-bold text-emerald-200">{stats.resolved}</div>
        </div>
        <div className="app-surface rounded-3xl p-6">
          <div className="app-kicker">Still Open</div>
          <div className="mt-3 text-3xl font-bold text-amber-100">{stats.pending}</div>
        </div>
        <div className="app-surface rounded-3xl p-6">
          <div className="app-kicker">Awaiting Citizen Confirmation</div>
          <div className="mt-3 text-3xl font-bold text-amber-100">{stats.awaiting_confirmation}</div>
        </div>
        <div className="app-surface rounded-3xl p-6">
          <div className="app-kicker">Pending Access Requests</div>
          <div className="mt-3 text-3xl font-bold text-cyan-100">{pendingRequests.length}</div>
        </div>
      </div>

      {error ? <div className="app-surface mb-4 rounded-2xl border border-red-400/30 bg-red-500/10 p-4 text-red-100">{error}</div> : null}
      {notice ? <div className="app-surface mb-4 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-4 text-emerald-100">{notice}</div> : null}

      <div className="app-surface rounded-[2rem] p-8 mb-8">
        <div className="mb-6 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="app-panel-title text-2xl">Authority / Admin Access Requests</h2>
            <p className="text-sm app-muted mt-1">Approve only verified registrations. Approved users can then log in.</p>
          </div>
          <div className="text-sm app-dim">Total users: {stats.total_users}</div>
        </div>

        {pendingRequests.length ? (
          <div className="overflow-x-auto">
            <table className="app-table text-sm">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Requested Role</th>
                  <th className="px-4 py-3 text-left font-medium">Name</th>
                  <th className="px-4 py-3 text-left font-medium">Office Details</th>
                  <th className="px-4 py-3 text-left font-medium">Reason</th>
                  <th className="px-4 py-3 text-left font-medium">Requested At</th>
                  <th className="px-4 py-3 text-left font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {pendingRequests.map((requestItem) => (
                  <tr key={requestItem.id} className="align-top">
                    <td className="px-4 py-3">
                      <span className="app-status app-status-active rounded-full px-3 py-1 text-xs font-semibold">
                        {requestItem.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-white">{requestItem.user?.full_name || "User"}</div>
                      <div className="text-xs app-dim">{requestItem.user?.email || ""}</div>
                      {requestItem.phone_number ? <div className="text-xs app-dim mt-1">{requestItem.phone_number}</div> : null}
                    </td>
                    <td className="px-4 py-3">
                      {requestItem.service_area ? <div><span className="font-medium text-white">Service Area:</span> {requestItem.service_area}</div> : null}
                      {requestItem.department ? <div><span className="font-medium text-white">Office:</span> {requestItem.department}</div> : null}
                      {requestItem.employee_id ? <div className="text-xs app-dim mt-1">ID: {requestItem.employee_id}</div> : null}
                    </td>
                    <td className="px-4 py-3 app-muted">{requestItem.access_reason || "No reason provided."}</td>
                    <td className="px-4 py-3 text-xs app-dim">{new Date(requestItem.created_at).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-2 sm:flex-row">
                        <button type="button" className="app-btn app-btn-success px-3 py-2 text-xs" onClick={() => approve(requestItem.id)}>
                          Approve
                        </button>
                        <button type="button" className="app-btn app-btn-danger px-3 py-2 text-xs" onClick={() => reject(requestItem.id)}>
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="app-empty rounded-2xl px-6 py-8 text-center">No pending authority or admin requests.</p>
        )}
      </div>

      <div className="app-surface rounded-[2rem] p-8">
        <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 className="app-panel-title text-2xl">Complaint Monitoring</h2>
            <p className="text-sm app-muted mt-1">Admins can inspect details, assignment progress, and trigger reminders.</p>
          </div>
          <form onSubmit={onFilterSubmit} className="flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by citizen, service area, ward, or description"
            />
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">All Status</option>
              {statusChoices.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
            <button type="submit" className="app-btn app-btn-secondary text-sm">Filter</button>
          </form>
        </div>

        {loading ? (
          <p className="app-empty rounded-2xl px-6 py-8 text-center">Loading complaints...</p>
        ) : complaints.length ? (
          <div className="overflow-x-auto">
            <table className="app-table text-sm">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Complaint</th>
                  <th className="px-4 py-3 text-left font-medium">Citizen</th>
                  <th className="px-4 py-3 text-left font-medium">Description</th>
                  <th className="px-4 py-3 text-left font-medium">Assigned Authority</th>
                  <th className="px-4 py-3 text-left font-medium">Timeline</th>
                  <th className="px-4 py-3 text-left font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {complaints.map((complaint) => (
                  <tr key={complaint.id} className="align-top">
                    <td className="px-4 py-3">
                      <div className="font-medium text-white">#{complaint.id} - {complaint.category_display}</div>
                      <div className="text-xs app-dim mt-1">{complaint.area}</div>
                      <div className="text-xs app-dim">{complaint.service_area}</div>
                      <div className="mt-2">
                        <span className={`app-status rounded-full px-2 py-1 text-xs font-medium ${badgeClass(complaint.status)}`}>
                          {complaint.status_display}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-white">{complaint.citizen?.full_name || "Citizen"}</div>
                      <div className="text-xs app-dim">{complaint.citizen?.email || ""}</div>
                    </td>
                    <td className="px-4 py-3 app-muted max-w-xs">{complaint.description}</td>
                    <td className="px-4 py-3">
                      {complaint.assigned_authority ? (
                        <>
                          <div className="font-medium text-white">{complaint.assigned_authority.full_name}</div>
                          <div className="text-xs app-dim">{complaint.assigned_authority.email}</div>
                        </>
                      ) : (
                        <span className="app-dim">Not assigned yet</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs app-dim space-y-1">
                      <div><span className="font-medium text-white/80">Filed:</span> {new Date(complaint.created_at).toLocaleString()}</div>
                      <div><span className="font-medium text-white/80">Acknowledged:</span> {complaint.acknowledged_at ? new Date(complaint.acknowledged_at).toLocaleString() : "Not yet"}</div>
                      <div><span className="font-medium text-white/80">Solved By Authority:</span> {complaint.resolution_requested_at ? new Date(complaint.resolution_requested_at).toLocaleString() : "Not yet"}</div>
                      <div><span className="font-medium text-white/80">Citizen Confirmed:</span> {complaint.citizen_confirmed_at ? new Date(complaint.citizen_confirmed_at).toLocaleString() : "Not yet"}</div>
                      <div><span className="font-medium text-white/80">Reminder Sent:</span> {complaint.last_reminder_sent_at ? new Date(complaint.last_reminder_sent_at).toLocaleString() : "Never"}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col items-start gap-2">
                        <Link href={`/complaint/${complaint.id}`} className="app-link">View full timeline</Link>
                        {complaint.assigned_authority && complaint.status !== "resolved" ? (
                          <button type="button" className="app-btn app-btn-warn px-3 py-2 text-xs" onClick={() => remind(complaint.id)}>
                            Email Authority
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="app-empty rounded-2xl px-6 py-8 text-center">No complaints found.</p>
        )}
      </div>
    </AppShell>
  );
}
