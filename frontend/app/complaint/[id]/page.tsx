"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import { useRoleGuard } from "@/lib/auth";
import { authGetJson, authPostJson, backendUrl } from "@/lib/backend";
import type { UserRole } from "@/lib/types";

type UserBrief = {
  id: number;
  email: string;
  full_name: string;
  username: string;
};

type ComplaintData = {
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
  resolved_at: string | null;
  generated_docx_url: string | null;
  generated_pdf_url: string | null;
  email_sent_at: string | null;
  email_error: string;
  citizen: UserBrief | null;
  assigned_authority: UserBrief | null;
};

type ActivityItem = {
  id: number;
  event_type_display: string;
  message: string;
  created_at: string;
  actor: UserBrief | null;
};

type UpdateItem = {
  id: number;
  message: string;
  created_at: string;
  updated_by: UserBrief | null;
};

type EvidenceImage = {
  id: number;
  name: string;
  url: string;
};

type ComplaintDetailResponse = {
  success: boolean;
  complaint: ComplaintData;
  permissions: {
    can_add_note: boolean;
    can_acknowledge: boolean;
    can_mark_resolved: boolean;
    can_confirm_resolution: boolean;
  };
  activities: ActivityItem[];
  updates: UpdateItem[];
  evidence_images: EvidenceImage[];
};

function statusClass(status: string) {
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

function roleHome(role: UserRole | null) {
  if (role === "admin") {
    return "/dashboard/admin";
  }
  if (role === "authority") {
    return "/authority";
  }
  return "/citizen";
}

export default function ComplaintDetailPage() {
  const { ready, role } = useRoleGuard(["citizen", "authority", "admin"]);
  const params = useParams<{ id: string }>();

  const complaintId = useMemo(() => Number(params.id), [params.id]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [detail, setDetail] = useState<ComplaintDetailResponse | null>(null);
  const [note, setNote] = useState("");

  async function loadDetail() {
    if (!Number.isFinite(complaintId) || complaintId <= 0) {
      setError("Invalid complaint id.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await authGetJson<ComplaintDetailResponse>(`/api/complaints/${complaintId}/`);
      setDetail(data);
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Failed to load complaint details.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!ready) {
      return;
    }
    void loadDetail();
  }, [ready, complaintId]);

  async function runAction(path: string, successMessage?: string) {
    setError(null);
    setNotice(null);
    try {
      const result = await authPostJson<{ success: boolean; message?: string }>(path, {});
      setNotice(result.message || successMessage || "Action completed.");
      await loadDetail();
    } catch (actionError) {
      const message = actionError instanceof Error ? actionError.message : "Action failed.";
      setError(message);
    }
  }

  async function submitNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!note.trim()) {
      return;
    }
    setError(null);
    setNotice(null);
    try {
      const result = await authPostJson<{ success: boolean; message: string }>(`/api/complaints/${complaintId}/notes/`, {
        message: note.trim(),
      });
      setNotice(result.message);
      setNote("");
      await loadDetail();
    } catch (actionError) {
      const message = actionError instanceof Error ? actionError.message : "Failed to add note.";
      setError(message);
    }
  }

  if (!ready || !role) {
    return null;
  }

  return (
    <AppShell
      role={role}
      title={detail ? `Complaint #${detail.complaint.id}` : "Complaint Detail"}
      subtitle="Track the full complaint timeline, notes, and resolution workflow in one native view."
    >
      <div className="mb-4">
        <Link href={roleHome(role)} className="app-link">Back to dashboard</Link>
      </div>

      {error ? <div className="app-surface mb-4 rounded-2xl border border-red-400/30 bg-red-500/10 p-4 text-red-100">{error}</div> : null}
      {notice ? <div className="app-surface mb-4 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-4 text-emerald-100">{notice}</div> : null}

      {loading || !detail ? (
        <p className="app-empty rounded-2xl px-6 py-8 text-center">Loading complaint details...</p>
      ) : (
        <div className="space-y-8">
          <div className="app-surface rounded-[2rem] p-8">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <h2 className="app-panel-title text-3xl">{detail.complaint.category_display}</h2>
                <p className="mt-2 text-sm app-muted">{detail.complaint.area}</p>
                <p className="mt-1 text-xs app-dim">{detail.complaint.service_area}</p>
              </div>
              <div>
                <span className={`app-status rounded-full px-3 py-1 text-sm font-medium ${statusClass(detail.complaint.status)}`}>
                  {detail.complaint.status_display}
                </span>
              </div>
            </div>

            <div className="grid gap-4 mt-8 md:grid-cols-2 xl:grid-cols-4">
              <div className="app-surface-soft rounded-xl p-4">
                <div className="app-kicker">Filed</div>
                <div className="mt-2 font-semibold text-white">{new Date(detail.complaint.created_at).toLocaleString()}</div>
              </div>
              <div className="app-surface-soft rounded-xl p-4">
                <div className="app-kicker">Acknowledged</div>
                <div className="mt-2 font-semibold text-white">{detail.complaint.acknowledged_at ? new Date(detail.complaint.acknowledged_at).toLocaleString() : "Not yet"}</div>
              </div>
              <div className="app-surface-soft rounded-xl p-4">
                <div className="app-kicker">Solved By Authority</div>
                <div className="mt-2 font-semibold text-white">{detail.complaint.resolution_requested_at ? new Date(detail.complaint.resolution_requested_at).toLocaleString() : "Not yet"}</div>
              </div>
              <div className="app-surface-soft rounded-xl p-4">
                <div className="app-kicker">Citizen Confirmed</div>
                <div className="mt-2 font-semibold text-white">{detail.complaint.citizen_confirmed_at ? new Date(detail.complaint.citizen_confirmed_at).toLocaleString() : "Pending"}</div>
              </div>
            </div>

            <div className="mt-8">
              <h3 className="app-panel-title text-xl mb-3">Description</h3>
              <p className="app-muted whitespace-pre-line">{detail.complaint.description}</p>
            </div>

            <div className="app-surface-soft mt-8 rounded-xl p-5">
              <h3 className="app-panel-title text-lg mb-4">Next Action</h3>
              <div className="flex flex-wrap gap-3">
                {detail.permissions.can_acknowledge ? (
                  <button type="button" className="app-btn app-btn-secondary text-sm" onClick={() => runAction(`/api/complaints/${complaintId}/acknowledge/`)}>
                    Acknowledge Complaint
                  </button>
                ) : null}

                {detail.permissions.can_mark_resolved ? (
                  <button type="button" className="app-btn app-btn-success text-sm" onClick={() => runAction(`/api/complaints/${complaintId}/request-resolution/`)}>
                    Mark as Solved
                  </button>
                ) : null}

                {detail.permissions.can_confirm_resolution ? (
                  <>
                    <button type="button" className="app-btn app-btn-success text-sm" onClick={() => runAction(`/api/complaints/${complaintId}/confirm-resolution/`)}>
                      Approve Resolution
                    </button>
                    <button type="button" className="app-btn app-btn-warn text-sm" onClick={() => runAction(`/api/complaints/${complaintId}/reopen/`)}>
                      Need More Work
                    </button>
                  </>
                ) : null}
              </div>
            </div>
          </div>

          {detail.complaint.generated_docx_url || detail.complaint.generated_pdf_url ? (
            <div className="app-surface rounded-[2rem] p-8">
              <h3 className="app-panel-title text-xl mb-4">Generated Application Files</h3>
              <div className="flex flex-wrap gap-3">
                {detail.complaint.generated_docx_url ? (
                  <a href={backendUrl(detail.complaint.generated_docx_url)} className="app-btn app-btn-primary inline-flex items-center gap-2" target="_blank" rel="noreferrer">
                    <i className="fas fa-file-word" /> Download DOCX
                  </a>
                ) : null}
                {detail.complaint.generated_pdf_url ? (
                  <a href={backendUrl(detail.complaint.generated_pdf_url)} className="app-btn app-btn-secondary inline-flex items-center gap-2" target="_blank" rel="noreferrer">
                    <i className="fas fa-file-pdf" /> Download PDF
                  </a>
                ) : null}
              </div>
              <div className="mt-3 text-sm app-muted">
                {detail.complaint.email_sent_at
                  ? `Authority notification sent on ${new Date(detail.complaint.email_sent_at).toLocaleString()}.`
                  : detail.complaint.email_error
                    ? `Notification issue: ${detail.complaint.email_error}`
                    : "Complaint notifications have not been attempted yet."}
              </div>
            </div>
          ) : null}

          {detail.evidence_images.length ? (
            <div className="app-surface rounded-[2rem] p-8">
              <h3 className="app-panel-title text-xl mb-4">Photo Evidence</h3>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {detail.evidence_images.map((image) => (
                  <a key={image.id} href={image.url} target="_blank" rel="noreferrer" className="app-surface-soft block rounded-xl overflow-hidden">
                    <img src={image.url} alt={image.name} className="h-48 w-full object-cover" />
                    <div className="p-3 text-sm app-muted">{image.name}</div>
                  </a>
                ))}
              </div>
            </div>
          ) : null}

          <div className="grid gap-8 xl:grid-cols-2">
            <div className="app-surface rounded-[2rem] p-8">
              <h3 className="app-panel-title text-xl mb-4">Activity Timeline</h3>
              {detail.activities.length ? (
                <div className="space-y-4">
                  {detail.activities.map((activity) => (
                    <div key={activity.id} className="app-surface-soft rounded-xl p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="font-semibold text-white">{activity.event_type_display}</div>
                          <div className="text-sm app-muted mt-1">{activity.actor ? activity.actor.full_name : "System"}</div>
                          {activity.message ? <div className="text-sm app-muted mt-2">{activity.message}</div> : null}
                        </div>
                        <div className="text-xs app-dim whitespace-nowrap">{new Date(activity.created_at).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-empty rounded-2xl px-6 py-8">No activity has been logged yet.</p>
              )}
            </div>

            <div className="space-y-8">
              <div className="app-surface rounded-[2rem] p-8">
                <h3 className="app-panel-title text-xl mb-4">Notes & Updates</h3>
                {detail.updates.length ? (
                  <div className="space-y-4">
                    {detail.updates.map((update) => (
                      <div key={update.id} className="app-surface-soft rounded-lg border-l-4 border-cyan-200/50 p-4">
                        <div className="flex justify-between items-start gap-4">
                          <div>
                            <div className="font-medium text-white">{update.updated_by?.full_name || "User"}</div>
                            <div className="text-sm app-muted mt-1">{update.message}</div>
                          </div>
                          <div className="text-xs app-dim whitespace-nowrap">{new Date(update.created_at).toLocaleString()}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="app-empty rounded-2xl px-6 py-8">No notes yet.</p>
                )}
              </div>

              {detail.permissions.can_add_note ? (
                <div className="app-surface rounded-[2rem] p-8">
                  <h3 className="app-panel-title text-xl mb-4">Add Note</h3>
                  <form onSubmit={submitNote} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2 text-white/80">Message</label>
                      <textarea rows={4} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Add an update note..." required />
                    </div>
                    <button type="submit" className="app-btn app-btn-primary">Save Note</button>
                  </form>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
