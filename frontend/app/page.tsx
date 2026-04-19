import Link from "next/link";

const journey = [
  {
    title: "Start in any language",
    detail: "Write naturally. The assistant keeps context and converts your issue into a structured complaint draft.",
  },
  {
    title: "Attach proof fast",
    detail: "Add photo evidence while chatting so location and severity are clearer for the assigned authority.",
  },
  {
    title: "Track progress clearly",
    detail: "Move from filing to acknowledgment and resolution with one timeline instead of scattered updates.",
  },
];

export default function HomePage() {
  return (
    <main className="home-root">
      <div className="home-orb a" />
      <div className="home-orb b" />
      <div className="home-orb c" />

      <div className="home-frame">
        <header className="home-nav">
          <div className="home-brand">
            <strong>Dhaka Nagorik AI</strong>
            <span>Civic Complaint Platform</span>
          </div>

          <div className="home-nav-actions">
            <button type="button" className="app-theme-toggle" data-theme-toggle>
              <span data-theme-label>Bright Mode</span>
            </button>
            <Link href="/login" className="home-cta login">
              Login
            </Link>
            <Link href="/signup" className="home-cta signup">
              Create Account
            </Link>
          </div>
        </header>

        <section className="home-main">
          <article className="home-hero">
            <span className="home-kicker">Dhaka Citizen Experience</span>
            <h1 className="home-title">
              Report real city issues with a <strong>clean, guided flow</strong>.
            </h1>
            <p className="home-subtitle">
              Dhaka Nagorik AI blends citizen reporting, authority workflows, and AI-assisted complaint intake in one place so people can
              explain problems quickly and officials can act with better context.
            </p>

            <div className="home-action-row">
              <Link href="/signup" className="primary">
                Start Reporting
              </Link>
              <Link href="/login" className="secondary">
                Continue to Dashboard
              </Link>
            </div>

            <div className="home-track">
              {journey.map((step) => (
                <div key={step.title} className="home-track-item">
                  <strong>{step.title}</strong>
                  <span>{step.detail}</span>
                </div>
              ))}
            </div>
          </article>

          <aside className="home-right">
            <section className="home-card">
              <h3>Complaint Pipeline</h3>
              <p>
                Citizen submission, AI extraction, authority acknowledgment, and citizen confirmation are connected end-to-end with less
                friction.
              </p>
            </section>

            <section className="home-card">
              <h3>Role Aware Platform</h3>
              <p>
                Citizens, authorities, and admins each get dedicated dashboards, with scoped controls and session-based access.
              </p>
            </section>

            <section className="home-card">
              <h3>Built For Fast Action</h3>
              <div className="home-stats">
                <div className="home-stat">
                  <strong>24/7</strong>
                  <span>Assistant Access</span>
                </div>
                <div className="home-stat">
                  <strong>3 Roles</strong>
                  <span>Citizen · Authority · Admin</span>
                </div>
                <div className="home-stat">
                  <strong>Live</strong>
                  <span>Timeline Tracking</span>
                </div>
              </div>
            </section>
          </aside>
        </section>
      </div>
    </main>
  );
}
