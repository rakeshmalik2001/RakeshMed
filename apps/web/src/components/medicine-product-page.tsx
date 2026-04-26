"use client";

import type { Route } from "next";
import Link from "next/link";

import { AddToCartButton } from "@/components/add-to-cart-button";
import { ProductRailCarousel } from "@/components/product-rail-carousel";
import type { CatalogProductDetail } from "@/lib/catalog-product-data";

function getLocationLabel(address: string) {
  const compactAddress = address.replace(/\s+/g, " ").trim();
  const pinMatch = compactAddress.match(/\b(\d{6})\b/);
  const addressParts = compactAddress
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);

  const city = addressParts.length >= 2 ? addressParts[addressParts.length - 2] : addressParts[0];
  const pin = pinMatch?.[1];

  if (city && pin) {
    return `${pin} ${city}`;
  }

  return city ?? "Location available at checkout";
}

function slugLabel(value: string) {
  return value
    .replace(/-/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getWarningIcon(iconKey: CatalogProductDetail["warningCards"][number]["iconKey"]) {
  switch (iconKey) {
    case "child":
      return "🧒";
    case "bottle":
      return "🧴";
    case "device":
      return "🩺";
    case "wash":
      return "🧼";
    case "droplet":
      return "💧";
    case "heart":
      return "❤";
    case "alert":
    default:
      return "⚠";
  }
}

function getAssuranceIcon(iconKey: CatalogProductDetail["assuranceItems"][number]["iconKey"]) {
  switch (iconKey) {
    case "alert":
      return "⚠";
    case "heart":
      return "❤";
    case "image":
      return "🖼";
    case "check":
    default:
      return "✓";
  }
}

export function MedicineProductPage({ product }: { product: CatalogProductDetail }) {
  const deliveryLocation = getLocationLabel(product.manufacturerDetails.address);

  return (
    <main className="page-shell medicine-page netmeds-pdp">
      <div className="netmeds-pdp-breadcrumb">
        {product.breadcrumbs.map((item, index) => (
          <span key={`${item.label}-${index}`}>
            {item.href ? <Link href={item.href as Route}>{item.label}</Link> : <span>{item.label}</span>}
            {index < product.breadcrumbs.length - 1 ? <span className="netmeds-pdp-breadcrumb-sep">{">"}</span> : null}
          </span>
        ))}
      </div>

      <section className="netmeds-pdp-hero">
        <div className="netmeds-pdp-gallery">
          <div className="netmeds-pdp-thumbs">
            <button type="button" className="netmeds-pdp-thumb-arrow" aria-label="View previous image">
              <span aria-hidden="true">˄</span>
            </button>
            {product.galleryItems.map((item, index) => (
              <button
                key={`${item.label}-${index}`}
                type="button"
                className={`netmeds-pdp-thumb ${index === 1 ? "is-active" : ""}`}
                aria-label={`View ${item.label}`}
              >
                <span className="netmeds-pdp-thumb-preview" />
                <strong>{item.label}</strong>
                <small>{item.meta}</small>
              </button>
            ))}
            <button type="button" className="netmeds-pdp-thumb-arrow" aria-label="View next image">
              <span aria-hidden="true">˅</span>
            </button>
          </div>

          <div className="netmeds-pdp-visual">
            <div className="netmeds-pdp-image-frame">
              <div className="netmeds-pdp-image-placeholder">
                <span className="netmeds-pdp-image-icon">
                  <span aria-hidden="true">🖼</span>
                </span>
                <strong>{product.name}</strong>
                <p>{product.pack}</p>
                <small>{product.brand}</small>
              </div>
            </div>
          </div>

          <AddToCartButton
            product={{
              slug: product.slug,
              name: product.name,
              off: product.off,
              mrp: product.mrp,
              price: product.price,
              meta: `${product.brand} | ${product.pack}`,
              rx: false
            }}
            className="netmeds-pdp-primary-cta"
            label="Add to cart"
          />
        </div>

        <div className="netmeds-pdp-summary">
          <div className="netmeds-pdp-headline">
            <div>
              <p className="netmeds-pdp-brand">{product.manufacturer}</p>
              <h1>{product.name}</h1>
              <div className="netmeds-pdp-tags">
                <span>Rx</span>
                <span>{slugLabel(product.breadcrumbs[product.breadcrumbs.length - 2]?.label ?? product.form)}</span>
              </div>
            </div>

            <div className="netmeds-pdp-head-actions">
              <button type="button">Save</button>
              <button type="button">Share</button>
            </div>
          </div>

          <div className="netmeds-pdp-price-card">
            <div className="netmeds-pdp-price-head">
              <span className="netmeds-pdp-best-price">
                <span aria-hidden="true">✓</span>
                Best price Rs.{product.price}
              </span>
              <span className="netmeds-pdp-price-off">{product.off}</span>
            </div>

            <div className="netmeds-pdp-price-row">
              <strong>Rs.{product.price}</strong>
              <span>{product.off}</span>
            </div>

            <div className="netmeds-pdp-mrp-row">
              <span>
                MRP <del>Rs.{product.mrp}</del>
              </span>
              <small>(Inclusive of all taxes)</small>
            </div>
          </div>

          <section className="netmeds-pdp-coupons">
            <div className="netmeds-pdp-section-bar">
              <h2>Coupons</h2>
              <button type="button">View all</button>
            </div>
            <div className="netmeds-pdp-coupon-grid">
              {product.coupons.map((coupon) => (
                <article key={`${coupon.title}-${coupon.badge}`} className="netmeds-pdp-coupon-card">
                  <div>
                    <strong>{coupon.title}</strong>
                    <p>{coupon.description}</p>
                  </div>
                  <span>{coupon.badge}</span>
                </article>
              ))}
            </div>
          </section>

          <section className="netmeds-pdp-delivery-card">
            <div>
              <h2>Deliver to</h2>
              <p>{deliveryLocation}</p>
              <strong>
                Delivery: {product.deliveryLabel} <span>In stock</span>
              </strong>
            </div>
            <button type="button" aria-label="Edit delivery location">
              <span aria-hidden="true">✎</span>
            </button>
          </section>
        </div>
      </section>

      <section className="netmeds-pdp-assurance">
        {product.assuranceItems.map(({ label, iconKey }) => {
          const icon = getAssuranceIcon(iconKey);

          return (
            <article key={label}>
              <span className="netmeds-pdp-assurance-icon">
                <span aria-hidden="true">{icon}</span>
              </span>
              <p>{label}</p>
            </article>
          );
        })}
      </section>

      <section className="netmeds-pdp-substitutes">
        <aside className="netmeds-pdp-substitutes-copy">
          <h2>Substitutes</h2>
          <p>Same composition as:</p>
          <strong>{product.name}</strong>
          <p>Contains:</p>
          <strong>{product.composition}</strong>
          <button type="button">More details</button>
        </aside>

        <div className="netmeds-pdp-substitutes-rail">
          {product.rails.manufacturerMore.length > 0 || product.rails.related.length > 0 ? (
            <ProductRailCarousel
              products={product.rails.manufacturerMore.length > 0 ? product.rails.manufacturerMore : product.rails.related}
              note="Save more with substitute"
              railLabel="substitutes"
            />
          ) : (
            <div className="empty-cart-box">
              <h2>Substitutes are not linked yet</h2>
              <p>Related and same-salt options will appear here when the catalog links them for this product.</p>
            </div>
          )}
        </div>
      </section>

      <section className="netmeds-pdp-membership">
        <div>
          <p className="netmeds-pdp-membership-kicker">{product.membership.kicker}</p>
          <h2>{product.membership.title}</h2>
        </div>
        <div className="netmeds-pdp-membership-features">
          {product.membership.features.map((feature) => (
            <span key={feature}>{feature}</span>
          ))}
        </div>
        <button type="button">{product.membership.ctaLabel}</button>
      </section>

      <section className="netmeds-pdp-quick-links">
        <h2>Quick Links</h2>
        <div className="netmeds-pdp-quick-links-row">
          {product.quickLinks.map((item) => (
            <a key={item.id} href={`#${item.id}`}>
              {item.label}
            </a>
          ))}
        </div>
      </section>

      <section className="netmeds-pdp-content">
        <article id="uses" className="netmeds-pdp-text-section">
          <h2>Uses Of {product.name.toUpperCase()}</h2>
          <ul>
            {product.keyUses.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article id="how-it-works" className="netmeds-pdp-text-section">
          <h2>How {product.name.toUpperCase()} Works</h2>
          <p>
            {product.name.toUpperCase()} is presented here with its composition, pack details, and guidance so users can
            understand where it fits into daily care or medicine comparison. The page is structured to make evaluation,
            safety review, and buying decisions easier before checkout.
          </p>
        </article>

        <article id="how-to-use" className="netmeds-pdp-text-section">
          <h2>How to use {product.name.toUpperCase()}</h2>
          {product.howToUse.map((item) => (
            <p key={item}>{item}</p>
          ))}
        </article>

        <article id="side-effects" className="netmeds-pdp-text-section">
          <h2>Side Effects Of {product.name.toUpperCase()}</h2>
          <p>Common points to review before use:</p>
          <ul>
            {product.safetyInformation.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="netmeds-pdp-text-section">
          <h2>How To Manage Side Effects</h2>
          <div className="netmeds-pdp-manage-grid">
            {product.safetyInformation.slice(0, 3).map((item, index) => (
              <div key={item}>
                <strong>{["Care note", "Daily caution", "Support tip"][index]}</strong>
                <p>{item}</p>
              </div>
            ))}
          </div>
        </article>

        <article id="warning-precautions" className="netmeds-pdp-text-section">
          <h2>Warning & Precautions</h2>
          <div className="netmeds-pdp-warning-list">
            {product.warningCards.map((item) => {
              const icon = getWarningIcon(item.iconKey);

              return (
                <div key={`${item.title}-${item.body}`} className="netmeds-pdp-warning-item">
                <div className="netmeds-pdp-warning-head">
                  <div className="netmeds-pdp-warning-title">
                    <span className="netmeds-pdp-warning-icon" aria-hidden="true">
                      {icon}
                    </span>
                    <strong>{item.title}</strong>
                  </div>
                  <span className={`netmeds-pdp-warning-pill tone-${item.tone}`}>{item.status}</span>
                </div>
                <p>{item.body}</p>
              </div>
              );
            })}
          </div>
        </article>

        <article id="interactions" className="netmeds-pdp-text-section">
          <h2>Interactions</h2>
          <p>Before using {product.name.toUpperCase()}, review the following notes:</p>
          <ul>
            {product.interactions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article id="synopsis" className="netmeds-pdp-text-section">
          <h2>Synopsis</h2>
          <dl className="netmeds-pdp-synopsis">
            {product.synopsis.map((item) => (
              <div key={item.label}>
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>
        </article>

        <article id="useful-tests" className="netmeds-pdp-text-section">
          <h2>Useful Diagnostic Tests</h2>
          <ul>
            {product.usefulTests.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article id="faq" className="netmeds-pdp-text-section">
          <h2>Frequently Asked Questions</h2>
          <div className="netmeds-pdp-faq-list">
            {product.faqs.map((item) => (
              <details key={item.question} className="netmeds-pdp-faq-item">
                <summary>{item.question}</summary>
                <p>{item.answer}</p>
              </details>
            ))}
          </div>
        </article>

        <article id="learn-more" className="netmeds-pdp-text-section">
          <h2>Learn More</h2>
          <div className="netmeds-pdp-manage-grid">
            {product.articleLinks.map((item) => (
              <div key={`${item.category}-${item.title}`}>
                <strong>{item.category}</strong>
                <p>{item.title}</p>
              </div>
            ))}
          </div>
          <div className="netmeds-pdp-manage-grid">
            {product.textLinkSections.map((item) => (
              <div key={item.heading}>
                <strong>{item.heading}</strong>
                <p>{item.text}</p>
              </div>
            ))}
          </div>
          {product.disclaimer?.length ? (
            <div className="netmeds-pdp-disclaimer">
              {product.disclaimer.map((item) => (
                <p key={item}>{item}</p>
              ))}
            </div>
          ) : null}
        </article>
      </section>

      <section className="netmeds-pdp-lower-rail">
        <div className="netmeds-pdp-section-bar">
          <h2>People also viewed</h2>
        </div>
        {product.rails.related.length > 0 ? (
          <ProductRailCarousel
            products={product.rails.related}
            note="Save more with substitute"
            railLabel="people also viewed"
          />
        ) : (
          <div className="empty-cart-box">
            <h2>Related products are updating</h2>
            <p>This rail appears when the live catalog has nearby products linked to this item.</p>
          </div>
        )}
      </section>

      <section className="netmeds-pdp-lower-rail">
        <div className="netmeds-pdp-section-bar">
          <h2>Top-Selling Health Essentials</h2>
        </div>
        {product.rails.topSelling.length > 0 ? (
          <ProductRailCarousel
            products={product.rails.topSelling}
            note="Popular picks in everyday care"
            railLabel="top-selling health essentials"
          />
        ) : (
          <div className="empty-cart-box">
            <h2>Top-selling rail is updating</h2>
            <p>We show this section only when live catalog recommendations are available.</p>
          </div>
        )}
      </section>
    </main>
  );
}
