type PagePlaceholderProps = {
  eyebrow: string;
  title: string;
  description: string;
  bullets: string[];
};

export function PagePlaceholder({
  eyebrow,
  title,
  description,
  bullets
}: PagePlaceholderProps) {
  return (
    <section className="page-shell">
      <div className="placeholder-card">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
        <div className="info-panel">
          <p className="eyebrow">What This Area Covers</p>
          <div className="placeholder-module-grid">
            {bullets.map((bullet) => (
              <article key={bullet} className="placeholder-module-card">
                <span className="placeholder-module-badge" aria-hidden="true">
                  +
                </span>
                <strong>{bullet}</strong>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
