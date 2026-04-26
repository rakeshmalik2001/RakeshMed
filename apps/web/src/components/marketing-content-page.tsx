import type { Route } from "next";
import Link from "next/link";
import type { MarketingPageContent } from "@/lib/storefront-content";

type MarketingContentPageProps = {
  slug: string;
  content: MarketingPageContent;
};

export function MarketingContentPage({
  slug,
  content
}: MarketingContentPageProps) {
  return (
    <main className="page-shell marketing-page-shell">
      <div className="breadcrumb">Home / {slug}</div>

      <section className="marketing-hero-card">
        <div className="marketing-hero-copy">
          <p className="eyebrow">{content.eyebrow}</p>
          <h1>{content.title}</h1>
          <p>{content.intro}</p>
        </div>

        <div className="marketing-highlight-grid">
          {content.highlights.map((item) => (
            <article key={item.label} className="marketing-highlight-card">
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </article>
          ))}
        </div>
      </section>

      <section className="marketing-section-grid">
        {content.sections.map((section) => (
          <article key={section.title} className="info-panel marketing-section-card">
            <h2>{section.title}</h2>
            <p>{section.body}</p>
            {section.points?.length ? (
              <ul className="clean-list marketing-list">
                {section.points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            ) : null}
            {section.callout ? <div className="marketing-callout">{section.callout}</div> : null}
          </article>
        ))}
      </section>

      {content.cards?.length ? (
        <section className="marketing-card-grid">
          {content.cards.map((card) => (
            <article key={card.title} className="marketing-link-card">
              <strong>{card.title}</strong>
              <p>{card.body}</p>
              {card.href && card.ctaLabel ? (
                <Link href={card.href as Route} className="marketing-inline-link">
                  {card.ctaLabel}
                </Link>
              ) : null}
            </article>
          ))}
        </section>
      ) : null}

      {content.faqs?.length ? (
        <section className="info-panel marketing-faq-panel">
          <div className="marketing-panel-head">
            <p className="eyebrow">Frequently Asked Questions</p>
            <h2>Questions customers are likely to ask here</h2>
          </div>

          <div className="marketing-faq-list">
            {content.faqs.map((item) => (
              <details key={item.question} className="marketing-faq-item">
                <summary>{item.question}</summary>
                <p>{item.answer}</p>
              </details>
            ))}
          </div>
        </section>
      ) : null}

      <section className="marketing-cta-card">
        <div>
          <p className="eyebrow">Next Step</p>
          <h2>{content.cta.title}</h2>
          <p>{content.cta.body}</p>
        </div>

        <div className="marketing-cta-actions">
          <Link href={content.cta.primaryHref as Route} className="button-primary">
            {content.cta.primaryLabel}
          </Link>
          {content.cta.secondaryHref && content.cta.secondaryLabel ? (
            <Link href={content.cta.secondaryHref as Route} className="button-secondary">
              {content.cta.secondaryLabel}
            </Link>
          ) : null}
        </div>
      </section>
    </main>
  );
}
