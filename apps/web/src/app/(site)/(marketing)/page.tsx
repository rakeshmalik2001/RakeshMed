"use client";

import type { Route } from "next";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  FiActivity,
  FiArrowUpRight,
  FiCheckCircle,
  FiChevronDown,
  FiClock,
  FiGift,
  FiHeart,
  FiMapPin,
  FiPackage,
  FiPercent,
  FiPhoneCall,
  FiRepeat,
  FiShield,
  FiStar,
  FiTruck,
  FiUploadCloud
} from "react-icons/fi";

import { HomepageCategoryShowcase } from "@/components/homepage-category-showcase";
import { ProductRailCarousel } from "@/components/product-rail-carousel";
import { SiteSearchBar } from "@/components/site-search-bar";
import { fetchCatalogCategories, fetchCatalogProducts, type ApiCatalogProductSummary } from "@/lib/api";
import { homepageContent } from "@/lib/homepage-content";
import { buildNavCatalog, type NavCategory } from "@/lib/nav-catalog";
import { siteContact } from "@/lib/storefront-content";
import type { StorefrontProduct } from "@/lib/storefront-data";

const homepageIconMap = {
  activity: FiActivity,
  "arrow-up-right": FiArrowUpRight,
  "check-circle": FiCheckCircle,
  clock: FiClock,
  gift: FiGift,
  heart: FiHeart,
  "map-pin": FiMapPin,
  package: FiPackage,
  percent: FiPercent,
  phone: FiPhoneCall,
  repeat: FiRepeat,
  shield: FiShield,
  truck: FiTruck,
  upload: FiUploadCloud
} as const;

function formatPrice(value: string) {
  const amount = Number.parseFloat(value);
  return Number.isNaN(amount) ? value : Number.isInteger(amount) ? String(amount) : amount.toFixed(2);
}

function discountFromPrices(mrp: string, salePrice: string) {
  const mrpValue = Number.parseFloat(mrp);
  const saleValue = Number.parseFloat(salePrice);

  if (Number.isNaN(mrpValue) || Number.isNaN(saleValue) || mrpValue <= 0 || saleValue >= mrpValue) {
    return "0% OFF";
  }

  return `${Math.round(((mrpValue - saleValue) / mrpValue) * 100)}% OFF`;
}

function mapApiProductsToStorefront(products: ApiCatalogProductSummary[]): StorefrontProduct[] {
  return products.map((product) => ({
    slug: product.slug,
    name: product.name,
    off: discountFromPrices(product.mrp, product.sale_price),
    mrp: formatPrice(product.mrp),
    price: formatPrice(product.sale_price),
    brand: product.brand?.name ?? product.manufacturer ?? "TrueCare",
    salt: product.composition || product.category.name,
    category: product.category.slug,
    form: product.dosage_form || "Product",
    useFor: product.category.name,
    tags: [product.stock_status.replace(/_/g, " "), product.requires_prescription ? "Prescription required" : "OTC"],
    meta: `${product.manufacturer || product.brand?.name || "TrueCare"} | ${product.pack_size || "Pack details"}`,
    rx: product.requires_prescription,
    pack: product.pack_size || "Pack of 1",
    uses: [product.category.name, product.composition || "Compare product details before purchase"]
  }));
}

export default function HomePage() {
  const [homepageShopCategories, setHomepageShopCategories] = useState<NavCategory[]>([]);
  const [popularItems, setPopularItems] = useState<StorefrontProduct[]>([]);
  const [dealItems, setDealItems] = useState<StorefrontProduct[]>([]);

  useEffect(() => {
    let isMounted = true;

    void fetchCatalogCategories()
      .then((items) => {
        if (!isMounted) {
          return;
        }

        const navigation = buildNavCatalog(items).filter((category) => (category.subcategories?.length ?? 0) > 0);
        setHomepageShopCategories(navigation);
      })
      .catch(() => {
        if (isMounted) {
          setHomepageShopCategories([]);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    void fetchCatalogProducts()
      .then((items) => {
        if (!isMounted || items.length === 0) {
          return;
        }

        const mapped = mapApiProductsToStorefront(items);
        setPopularItems(mapped.slice(0, 14));
        setDealItems(
          mapped
            .filter((product) => product.off !== "0% OFF" || product.category.includes("vitamins") || product.category.includes("heart"))
            .slice(0, 14)
        );
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }
        setPopularItems([]);
        setDealItems([]);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <main>
      <section className="hero-banner">
        <div className="hero-left-art" aria-hidden="true">
          <div className="hero-floating-pack hero-pack-tall">
            <span className="hero-pack-brand">TrueCare</span>
            <strong>RX</strong>
            <small>Daily essentials</small>
          </div>
        </div>
        <div className="hero-right-art" aria-hidden="true">
          <div className="hero-orbit-card">
            <span className="hero-orbit-icon">
              <FiPackage />
            </span>
            <div>
              <strong>Medicine guidance</strong>
              <p>Search, compare, and refill with clearer decision support.</p>
            </div>
          </div>
          <div className="hero-floating-pack hero-pack-wide">
            <span className="hero-pack-brand">TrueCare Plus</span>
            <strong>Care Plan</strong>
            <small>Refills | savings | support</small>
          </div>
        </div>
        <div className="hero-content">
          <p className="hero-kicker">{homepageContent.hero.kicker}</p>
          <h1>{homepageContent.hero.title}</h1>
          <p>{homepageContent.hero.description}</p>
          <div className="hero-search">
            <SiteSearchBar animatedTerms={homepageContent.hero.searchTerms} showButtonLabel={false} />
          </div>
          <div className="hero-benefits">
            {homepageContent.hero.benefits.map(({ label, iconKey }) => {
              const Icon = homepageIconMap[iconKey];

              return (
                <span key={label} className="hero-benefit-chip">
                <Icon />
                {label}
              </span>
              );
            })}
          </div>
          <div className="hero-stats-row">
            {homepageContent.hero.stats.map((item) => (
              <article key={item.label} className="hero-stat-card">
                <strong>{item.value}</strong>
                <span>{item.label}</span>
              </article>
            ))}
          </div>
        </div>
      </section>

      <div className="page-shell">
        <div className="section-stack">
          <section className="hero-trust-grid">
            {homepageContent.trustPoints.map(({ title, description, iconKey }) => {
              const Icon = homepageIconMap[iconKey];

              return (
                <article key={title} className="hero-trust-card">
                <span className="hero-trust-icon">
                  <Icon />
                </span>
                <div>
                  <h3>{title}</h3>
                  <p>{description}</p>
                </div>
              </article>
              );
            })}
          </section>

          <section>
            <div className="section-title-row">
              <h2>Quick actions</h2>
            </div>
            <div className="quick-actions-grid">
              {homepageContent.quickActions.map(({ title, description, href, iconKey }) => {
                const Icon = homepageIconMap[iconKey];

                return (
                  <Link key={title} href={href as Route} className="quick-action-card">
                  <span className="quick-action-icon">
                    <Icon />
                  </span>
                  <div className="quick-action-copy">
                    <h3>{title}</h3>
                    <p>{description}</p>
                  </div>
                  <span className="quick-action-arrow" aria-hidden="true">
                    <FiArrowUpRight />
                  </span>
                </Link>
                );
              })}
            </div>
          </section>

          <section>
            <div className="section-title-row action-strip-heading">
              <span className="section-divider" />
              <h2>Place your order via</h2>
              <span className="section-divider" />
            </div>
            <div className="order-actions">
              <a href={`tel:${siteContact.phone}`} className="action-card">
                <span className="action-icon">
                  <FiPhoneCall />
                </span>
                <div className="action-copy">
                  <span className="action-title">Call {siteContact.phone}</span>
                  <span className="action-subtitle">to place order</span>
                </div>
              </a>
              <Link href={"/upload-prescription" as Route} className="action-card">
                <span className="action-icon">
                  <FiUploadCloud />
                </span>
                <div className="action-copy">
                  <span className="action-title">Upload a</span>
                  <span className="action-subtitle">prescription</span>
                </div>
              </Link>
            </div>
          </section>

          <section className="prescription-care-section">
            <div className="prescription-care-copy">
              <div className="section-title-row prescription-title-row">
                <h2>{homepageContent.prescriptionCare.title}</h2>
              </div>
              <p className="prescription-care-intro">
                {homepageContent.prescriptionCare.intro}
              </p>

              <div className="prescription-step-list">
                {homepageContent.prescriptionCare.steps.map((step, index) => (
                  <article key={step.title} className="prescription-step-card">
                    <span className="prescription-step-index">0{index + 1}</span>
                    <div>
                      <h3>{step.title}</h3>
                      <p>{step.description}</p>
                    </div>
                  </article>
                ))}
              </div>
            </div>

            <aside className="prescription-care-panel">
              <p className="prescription-care-kicker">{homepageContent.prescriptionCare.panelKicker}</p>
              <h3>{homepageContent.prescriptionCare.panelTitle}</h3>
              <ul className="prescription-highlight-list">
                {homepageContent.prescriptionCare.highlights.map((item) => (
                  <li key={item}>
                    <FiCheckCircle />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              <div className="prescription-care-actions">
                <Link href={"/upload-prescription" as Route} className="prescription-primary-action">
                  Upload prescription
                </Link>
                <a href={`tel:${siteContact.phone}`} className="prescription-secondary-action">
                  Call support
                </a>
              </div>
            </aside>
          </section>

          <section className="substitutes-section">
            <div className="substitutes-card">
              <div className="substitutes-media" aria-hidden="true">
                <div className="substitutes-visual">
                  <div className="substitutes-pack substitutes-pack-main">
                    <span>Brand</span>
                    <strong>Rx Pack</strong>
                  </div>
                  <div className="substitutes-arrow">
                    <FiChevronDown />
                  </div>
                  <div className="substitutes-pack substitutes-pack-alt">
                    <span>Smarter match</span>
                    <strong>Care Pack</strong>
                  </div>
                </div>
              </div>

              <div className="substitutes-content">
                <div className="substitutes-header">
                  <h3>{homepageContent.substitutes.title}</h3>
                  <Link href={homepageContent.substitutes.learnMoreHref as Route} className="substitutes-link">
                    Learn more
                  </Link>
                </div>

                <div className="substitutes-benefits">
                  {homepageContent.substitutes.benefits.map(({ title, description, iconKey }) => {
                    const Icon = homepageIconMap[iconKey];

                    return (
                      <div key={title} className="substitute-benefit">
                      <div className="substitute-benefit-icon">
                        <Icon />
                      </div>
                      <div className="substitute-benefit-copy">
                        <p className="substitute-benefit-title">{title}</p>
                        <p className="substitute-benefit-text">{description}</p>
                      </div>
                    </div>
                    );
                  })}
                </div>

                <div className="substitutes-footer">
                  <div className="substitutes-footer-icon">
                    <FiHeart />
                  </div>
                  <p>
                    All Substitutes are made by <span>top 1% medicine manufacturers</span>
                  </p>
                </div>
              </div>
            </div>

            <p className="substitutes-example">
              <Link href={homepageContent.substitutes.exampleHref as Route}>View Example</Link> to compare and understand
            </p>
          </section>

          <section className="soft-section">
            <div className="section-title-row">
              <h2>Shop by categories</h2>
            </div>
            <HomepageCategoryShowcase categories={homepageShopCategories} />
          </section>

          <section>
            <div className="section-title-row">
              <h2>Popular items</h2>
            </div>
            {popularItems.length > 0 ? (
              <ProductRailCarousel
                products={popularItems}
                note="Save more with substitute ->"
                railLabel="popular items"
              />
            ) : (
              <div className="empty-cart-box">
                <h2>Popular items are updating</h2>
                <p>Live catalog rails will appear here once product data is available.</p>
              </div>
            )}
          </section>

          <section>
            <div className="section-title-row">
              <h2>Deals you&apos;ll love</h2>
            </div>
            {dealItems.length > 0 ? (
              <ProductRailCarousel
                products={dealItems}
                note="Special deal for limited-time savings"
                railLabel="deals you'll love"
              />
            ) : (
              <div className="empty-cart-box">
                <h2>Deals are updating</h2>
                <p>Current offers will appear here after the live catalog and pricing data load.</p>
              </div>
            )}
          </section>

          <section className="insights-layout">
            <div className="editorial-panel">
              <div className="section-title-row">
                <h2>{homepageContent.editorial.title}</h2>
                <Link href={homepageContent.editorial.viewAllHref as Route} className="section-link">
                  View All
                </Link>
              </div>
              <div className="editorial-lead-card">
                <div className="editorial-lead-visual">
                  <span className="editorial-lead-badge">{homepageContent.editorial.articles[0].tag}</span>
                  <div className="editorial-lead-orb" />
                </div>
                <div className="editorial-lead-copy">
                  <h3>{homepageContent.editorial.articles[0].title}</h3>
                  <p>{homepageContent.editorial.articles[0].summary}</p>
                  <Link href={homepageContent.editorial.articles[0].href as Route} className="editorial-link">
                    Read article
                    <FiArrowUpRight />
                  </Link>
                </div>
              </div>
              <div className="editorial-list">
                {homepageContent.editorial.articles.slice(1).map((article) => (
                  <article key={article.title} className="editorial-list-item">
                    <span className="editorial-list-tag">{article.tag}</span>
                    <div>
                      <h3>{article.title}</h3>
                      <p>{article.summary}</p>
                    </div>
                    <Link href={article.href as Route} className="editorial-link" aria-label={`Read ${article.title}`}>
                      <FiArrowUpRight />
                    </Link>
                  </article>
                ))}
              </div>
            </div>

            <div className="trust-stack">
              <section className="testimonial-band">
                <div className="section-title-row">
                  <h2>{homepageContent.testimonials.title}</h2>
                </div>
                <div className="mini-testimonial-grid">
                  {homepageContent.testimonials.stories.map((story) => (
                    <article key={story.name} className="mini-testimonial-card">
                      <div className="mini-testimonial-head">
                        <span className="mini-testimonial-stars">
                          <FiStar />
                          <FiStar />
                          <FiStar />
                          <FiStar />
                          <FiStar />
                        </span>
                        <span className="mini-testimonial-role">{story.role}</span>
                      </div>
                      <p>{story.quote}</p>
                      <strong>{story.name}</strong>
                    </article>
                  ))}
                </div>
              </section>

              <section className="faq-panel faq-panel-compact">
                <div className="section-title-row">
                  <h2>{homepageContent.faq.title}</h2>
                  <Link href={homepageContent.faq.viewAllHref as Route} className="section-link">
                    View all
                  </Link>
                </div>
                <div className="faq-list">
                  {homepageContent.faq.items.map((item, index) => (
                    <details key={item.question} className="faq-item" open={index === 0}>
                      <summary>
                        <p>{item.question}</p>
                        <span className="faq-icon">
                          <FiChevronDown />
                        </span>
                      </summary>
                      <div className="faq-answer">
                        <p>{item.answer}</p>
                      </div>
                    </details>
                  ))}
                </div>
              </section>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
