export default function AuthLayout({ eyebrow, title, description, children, footer }) {
  return (
    <div className="account-page">
      <aside className="account-brand-panel" aria-label="About Stress Monitor">
        <div className="account-brand-lockup">
          <span className="account-brand-mark" aria-hidden="true">SM</span>
          <div>
            <p className="account-brand-name">Stress Monitor</p>
            <p className="account-brand-tagline">Research-based stress classification</p>
          </div>
        </div>

        <div className="account-brand-copy">
          <span className="account-kicker">WESAD · XGBoost · 45 features</span>
          <h1>Understand physiological patterns with a clearer, evidence-led dashboard.</h1>
          <p>
            Explore anonymised research samples, view model confidence, and keep your account
            preferences in one secure place.
          </p>
        </div>

        <div className="account-feature-list" aria-label="Platform features">
          <div><span>01</span><p><strong>Research traceability</strong>Original WESAD participant IDs remain visible.</p></div>
          <div><span>02</span><p><strong>Transparent predictions</strong>See confidence and class probabilities.</p></div>
          <div><span>03</span><p><strong>Privacy-conscious profile</strong>Only practical context is requested.</p></div>
        </div>

        <p className="account-disclaimer">
          This prototype supports research and education. It does not provide a medical diagnosis.
        </p>
      </aside>

      <main className="account-main">
        <section className="auth-card">
          <header className="auth-card-header">
            <span className="auth-eyebrow">{eyebrow}</span>
            <h2>{title}</h2>
            {description && <p>{description}</p>}
          </header>
          {children}
          {footer && <div className="auth-card-footer">{footer}</div>}
        </section>
      </main>
    </div>
  );
}
