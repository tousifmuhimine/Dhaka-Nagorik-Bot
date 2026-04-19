"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import { authGetJson, authPostForm } from "@/lib/backend";
import { useRoleGuard } from "@/lib/auth";

type UserBrief = {
  id: number;
  email: string;
  full_name: string;
  username: string;
};

type ComplaintItem = {
  id: number;
  category: string;
  category_display: string;
  area: string;
  service_area: string;
  description: string;
  status: string;
  status_display: string;
  created_at: string;
  assigned_authority: UserBrief | null;
};

type Choice = {
  value: string | number;
  label: string;
};

type CitizenDashboardResponse = {
  success: boolean;
  stats: {
    total: number;
    resolved: number;
    pending_total: number;
  };
  complaints: ComplaintItem[];
  meta: {
    category_choices: Choice[];
    city_corporation_choices: Choice[];
    ward_choices: Choice[];
  };
};

type CitizenCreateResponse = {
  success: boolean;
  message: string;
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

export default function CitizenPage() {
  const { ready, role } = useRoleGuard(["citizen"]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [stats, setStats] = useState({ total: 0, resolved: 0, pending_total: 0 });
  const [complaints, setComplaints] = useState<ComplaintItem[]>([]);
  const [categoryChoices, setCategoryChoices] = useState<Choice[]>([]);
  const [cityChoices, setCityChoices] = useState<Choice[]>([]);
  const [wardChoices, setWardChoices] = useState<Choice[]>([]);

  const [category, setCategory] = useState("");
  const [cityCorporation, setCityCorporation] = useState("");
  const [wardNumber, setWardNumber] = useState("");
  const [thana, setThana] = useState("");
  const [area, setArea] = useState("");
  const [description, setDescription] = useState("");
  const [photos, setPhotos] = useState<File[]>([]);

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    try {
      const data = await authGetJson<CitizenDashboardResponse>("/api/dashboard/citizen/");
      setStats(data.stats);
      setComplaints(data.complaints);
      setCategoryChoices(data.meta.category_choices);
      setCityChoices(data.meta.city_corporation_choices);
      setWardChoices(data.meta.ward_choices);
      if (!category && data.meta.category_choices.length) {
        setCategory(String(data.meta.category_choices[0].value));
      }
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Failed to load dashboard.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!ready || role !== "citizen") {
      return;
    }
    void loadDashboard();
  }, [ready, role]);

  const selectedPhotoLabel = useMemo(() => {
    if (!photos.length) {
      return "No photos selected.";
    }
    if (photos.length === 1) {
      return photos[0].name;
    }
    return `${photos.length} photos selected`;
  }, [photos]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setNotice(null);

    try {
      const formData = new FormData();
      formData.append("category", category);
      formData.append("city_corporation", cityCorporation);
      formData.append("ward_number", wardNumber);
      formData.append("thana", thana);
      formData.append("area", area);
      formData.append("description", description);
      photos.forEach((photo) => formData.append("photos", photo));

      const result = await authPostForm<CitizenCreateResponse>("/api/dashboard/citizen/complaints/", formData);
      setNotice(result.message || "Complaint filed successfully.");
      setThana("");
      setArea("");
      setDescription("");
      setPhotos([]);
      await loadDashboard();
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : "Failed to submit complaint.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!ready || role !== "citizen") {
    return null;
  }

  return (
    <AppShell
      role="citizen"
      title="Citizen Dashboard"
      subtitle="File complaints and track every status update without leaving the native app."
    >
      <div className="grid gap-4 mb-8 md:grid-cols-3">
        <div className="app-surface rounded-3xl p-6">
          <div className="app-kicker">Total Complaints</div>
          <div className="mt-3 text-3xl font-bold text-white">{stats.total}</div>
        </div>
        <div className="app-surface rounded-3xl p-6">
          <div className="app-kicker">Resolved</div>
          <div className="mt-3 text-3xl font-bold text-emerald-200">{stats.resolved}</div>
        </div>
        <div className="app-surface rounded-3xl p-6">
          <div className="app-kicker">Still Open</div>
          <div className="mt-3 text-3xl font-bold text-amber-100">{stats.pending_total}</div>
        </div>
      </div>

      {error ? <div className="app-surface mb-4 rounded-2xl border border-red-400/30 bg-red-500/10 p-4 text-red-100">{error}</div> : null}
      {notice ? <div className="app-surface mb-4 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-4 text-emerald-100">{notice}</div> : null}

      <div className="grid gap-8 xl:grid-cols-2">
        <div className="app-surface rounded-[2rem] p-8">
          <h2 className="app-panel-title text-2xl mb-6">
            <i className="fas fa-file-alt" /> File New Complaint
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2 text-white/80">Category</label>
              <select value={category} onChange={(event) => setCategory(event.target.value)} required>
                {categoryChoices.map((item) => (
                  <option key={String(item.value)} value={String(item.value)}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-white/80">City Corporation</label>
              <select value={cityCorporation} onChange={(event) => setCityCorporation(event.target.value)} required>
                <option value="">Select city corporation</option>
                {cityChoices.map((item) => (
                  <option key={String(item.value)} value={String(item.value)}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-white/80">Ward Number</label>
              <select value={wardNumber} onChange={(event) => setWardNumber(event.target.value)} required>
                <option value="">Select ward</option>
                {wardChoices.map((item) => (
                  <option key={String(item.value)} value={String(item.value)}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-white/80">Neighborhood / Thana Label</label>
              <input
                type="text"
                value={thana}
                onChange={(event) => setThana(event.target.value)}
                placeholder="Neighborhood / thana"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-white/80">Area / Location</label>
              <input
                type="text"
                value={area}
                onChange={(event) => setArea(event.target.value)}
                placeholder="Specific location"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-white/80">Description</label>
              <textarea
                rows={5}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Describe your complaint"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-white/80">Photo Evidence</label>
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                multiple
                onChange={(event) => setPhotos(Array.from(event.target.files || []))}
              />
              <p className="mt-2 text-xs app-dim">{selectedPhotoLabel}</p>
            </div>

            <button type="submit" className="app-btn app-btn-primary w-full" disabled={isSubmitting}>
              <i className="fas fa-paper-plane" /> {isSubmitting ? "Submitting..." : "Submit Complaint"}
            </button>
          </form>
        </div>

        <div className="app-surface rounded-[2rem] p-8">
          <h2 className="app-panel-title text-2xl mb-6">
            <i className="fas fa-list" /> Your Complaints
          </h2>

          {loading ? (
            <p className="app-empty rounded-2xl px-6 py-8 text-center">Loading complaints...</p>
          ) : complaints.length ? (
            <div className="space-y-3">
              {complaints.map((complaint) => (
                <Link key={complaint.id} href={`/complaint/${complaint.id}`} className="app-surface-soft block rounded-2xl p-4 transition hover:bg-white/10">
                  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div>
                      <div className="font-medium text-white">
                        Complaint #{complaint.id} - {complaint.category_display}
                      </div>
                      <div className="mt-1 text-sm app-muted">{complaint.area}</div>
                      <div className="mt-1 text-xs app-dim">{complaint.service_area}</div>
                      <div className="mt-1 text-xs app-dim">Filed {new Date(complaint.created_at).toLocaleString()}</div>
                      {complaint.assigned_authority ? (
                        <div className="mt-1 text-xs app-dim">Assigned authority: {complaint.assigned_authority.full_name}</div>
                      ) : null}
                    </div>
                    <span className={`app-status rounded-full px-3 py-1 text-xs font-medium ${badgeClass(complaint.status)}`}>
                      {complaint.status_display}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <p className="app-empty rounded-2xl px-6 py-8 text-center">No complaints filed yet.</p>
          )}
        </div>
      </div>
    </AppShell>
  );
}
