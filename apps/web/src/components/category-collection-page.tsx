"use client";

import type { Route } from "next";
import Link from "next/link";
import { startTransition, type CSSProperties, useMemo, useState } from "react";

import { AddToCartButton } from "@/components/add-to-cart-button";
import { ProductRailCarousel } from "@/components/product-rail-carousel";
import type { ResolvedCategoryPage } from "@/lib/category-page-data";

function ProductVisual({ brand, accent }: { brand: string; accent: string }) {
  const initials = brand
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  return (
    <div className="skin-cream-visual" style={{ "--collection-accent": accent } as CSSProperties}>
      <div className="skin-cream-packaging">
        <span>{initials}</span>
      </div>
      <div className="skin-cream-pack-shadow" />
    </div>
  );
}

export function CategoryCollectionPage({
  breadcrumbs,
  title,
  categoryOptions,
  subcategoryOptions,
  brandOptions,
  products,
  content,
  faqs
}: ResolvedCategoryPage) {
  const [selectedBrands, setSelectedBrands] = useState<string[]>([]);
  const [sort, setSort] = useState<"featured" | "priceLow" | "discountHigh">("featured");
  const [page, setPage] = useState(1);
  const itemsPerPage = 10;

  const filteredProducts = useMemo(() => {
    const next = products.filter((product) => selectedBrands.length === 0 || selectedBrands.includes(product.brand));

    if (sort === "priceLow") {
      return [...next].sort((a, b) => Number(a.price) - Number(b.price));
    }

    if (sort === "discountHigh") {
      return [...next].sort((a, b) => Number.parseInt(b.off, 10) - Number.parseInt(a.off, 10));
    }

    return next;
  }, [products, selectedBrands, sort]);

  const totalPages = Math.max(1, Math.ceil(filteredProducts.length / itemsPerPage));
  const safePage = Math.min(page, totalPages);
  const paginatedProducts = filteredProducts.slice((safePage - 1) * itemsPerPage, safePage * itemsPerPage);

  function toggleBrand(brand: string) {
    startTransition(() => {
      setSelectedBrands((current) =>
        current.includes(brand) ? current.filter((item) => item !== brand) : [...current, brand]
      );
      setPage(1);
    });
  }

  function resetBrowseFilters() {
    startTransition(() => {
      setSelectedBrands([]);
      setSort("featured");
      setPage(1);
    });
  }

  const collectionRailProducts = useMemo(
    () =>
      products.map((product) => ({
        slug: product.slug,
        name: product.name,
        off: product.off,
        mrp: product.mrp,
        price: product.price,
        brand: product.brand,
        salt: product.brand,
        category: title,
        form: "OTC Product",
        useFor: title,
        tags: [product.brand, product.off],
        meta: `${product.brand} | ${title}`,
        rx: false,
        pack: `${title} selection`,
        uses: [title]
      })),
    [products, title]
  );
  const peopleAlsoViewedProducts = useMemo(
    () => collectionRailProducts.slice(0, 10),
    [collectionRailProducts]
  );
  const topSellingHealthEssentialsProducts = useMemo(
    () =>
      [...collectionRailProducts].sort(
        (left, right) => Number.parseInt(right.off, 10) - Number.parseInt(left.off, 10)
      ),
    [collectionRailProducts]
  );

  return (
    <main className="page-shell skin-cream-page">
      <div className="breadcrumb skin-cream-breadcrumb">
        {breadcrumbs.map((item, index) => (
          <span key={`${item.label}-${index}`}>
            {item.href ? <Link href={item.href as Route}>{item.label}</Link> : <span>{item.label}</span>}
            {index < breadcrumbs.length - 1 ? " / " : ""}
          </span>
        ))}
      </div>

      <div className="skin-cream-layout">
        <aside className="skin-cream-sidebar">
          <h2>Filters</h2>

          <section className="skin-filter-card">
            <div className="skin-filter-head">
              <span>Category</span>
              <button type="button">Clear</button>
            </div>
            <div className="skin-filter-list">
              {categoryOptions.map((item) => (
                <Link key={item.label} href={item.href as Route} className={`skin-filter-link ${item.active ? "active" : ""}`}>
                  <span className="skin-radio" />
                  <span>{item.label}</span>
                </Link>
              ))}
            </div>
          </section>

          {subcategoryOptions.length > 0 ? (
            <section className="skin-filter-card">
              <div className="skin-filter-head">
                <span>Sub-category</span>
                <button type="button">Clear</button>
              </div>
              <div className="skin-filter-list">
                {subcategoryOptions.map((item) => (
                  <Link key={item.label} href={item.href as Route} className={`skin-filter-link ${item.active ? "active" : ""}`}>
                    <span className="skin-radio" />
                    <span>{item.label}</span>
                  </Link>
                ))}
              </div>
            </section>
          ) : null}

          <section className="skin-filter-card">
            <div className="skin-filter-head">
              <span>Brands</span>
              <button type="button" onClick={() => setSelectedBrands([])} disabled={selectedBrands.length === 0}>
                Clear
              </button>
            </div>
            <div className="skin-filter-list checkbox-list">
              {brandOptions.map((item) => (
                <label key={item} className="skin-checkbox-row">
                  <input
                    type="checkbox"
                    checked={selectedBrands.includes(item)}
                    onChange={() => toggleBrand(item)}
                  />
                  <span>{item}</span>
                </label>
              ))}
            </div>
          </section>
        </aside>

        <section className="skin-cream-main">
          <header className="skin-cream-header">
            <div>
              <h1>{title}</h1>
              <p className="skin-cream-summary">
                Showing {filteredProducts.length} products{selectedBrands.length > 0 ? ` for ${selectedBrands.join(", ")}` : ""}.
              </p>
            </div>
            <div className="skin-cream-tools">
              <div className="skin-sort-row">
                {[
                  { label: "Featured", value: "featured" },
                  { label: "Price Low", value: "priceLow" },
                  { label: "Top Discount", value: "discountHigh" }
                ].map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`skin-sort-chip ${sort === option.value ? "active" : ""}`}
                    onClick={() => {
                      startTransition(() => {
                        setSort(option.value as typeof sort);
                        setPage(1);
                      });
                    }}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              <button type="button" className="skin-reset-button" onClick={resetBrowseFilters}>
                Reset filters
              </button>
            </div>
          </header>

          {selectedBrands.length > 0 ? (
            <div className="skin-active-filters">
              {selectedBrands.map((brand) => (
                <button key={brand} type="button" className="skin-active-filter-chip" onClick={() => toggleBrand(brand)}>
                  {brand} x
                </button>
              ))}
            </div>
          ) : null}

          <div className="skin-cream-grid">
            {paginatedProducts.map((product) => (
              <article key={product.name} className="skin-product-card">
                <span className="skin-product-off">{product.off}</span>
                <Link href={`/medicine/${product.slug}` as Route} className="skin-product-link">
                  <ProductVisual brand={product.brand} accent={product.accent} />
                  <h3>{product.name}</h3>
                  <div className="skin-product-divider" />
                  <div className="skin-product-meta">
                    <span>MRP Rs. {product.mrp}</span>
                    <strong>Rs. {product.price}</strong>
                  </div>
                </Link>
                <AddToCartButton
                  className="skin-product-button"
                  label="Add"
                  product={{
                    slug: product.slug,
                    name: product.name,
                    off: product.off,
                    mrp: product.mrp,
                    price: product.price,
                    meta: `${product.brand} | Recommended pack`,
                    rx: false
                  }}
                />
              </article>
            ))}
          </div>

          {filteredProducts.length === 0 ? (
            <div className="skin-empty-state">
              <h2>No products match these filters</h2>
              <p>Try clearing a brand filter or switching back to Featured to see the full collection again.</p>
              <button type="button" className="skin-reset-button" onClick={resetBrowseFilters}>
                Show all products
              </button>
            </div>
          ) : (
            <div className="skin-pagination-wrap">
              <p className="skin-pagination-summary">
                Page {safePage} of {totalPages}
              </p>
              <div className="skin-pagination">
                <button type="button" onClick={() => setPage(Math.max(1, safePage - 1))} disabled={safePage === 1}>
                  Prev
                </button>
                {Array.from({ length: totalPages }, (_, index) => index + 1).map((pageNumber) => (
                  <button
                    key={pageNumber}
                    type="button"
                    className={safePage === pageNumber ? "active" : ""}
                    onClick={() => setPage(pageNumber)}
                  >
                    {pageNumber}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setPage(Math.min(totalPages, safePage + 1))}
                  disabled={safePage === totalPages}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </section>
      </div>

      <section className="skin-cream-content">
        {content.map((section) => (
          <article key={section.heading} className="skin-copy-block">
            <h2>{section.heading}</h2>
            {section.intro ? <p>{section.intro}</p> : null}
            <ul>
              {section.bullets.map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
            {section.outro ? <p>{section.outro}</p> : null}
          </article>
        ))}
      </section>

      <section className="skin-faq-section">
        <h2>Frequently Asked Questions (FAQs)</h2>
        <div className="skin-faq-list">
          {faqs.map((item) => (
            <article key={item.question} className="skin-faq-card">
              <h3>{item.question}</h3>
              <p>{item.answer}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="skin-lower-rail">
        <h2>People also viewed</h2>
        <ProductRailCarousel
          products={peopleAlsoViewedProducts}
          note="Trending in this collection"
          railLabel="people also viewed"
        />
      </section>

      <section className="skin-lower-rail">
        <h2>Top-Selling Health Essentials</h2>
        <ProductRailCarousel
          products={topSellingHealthEssentialsProducts}
          note="Popular picks in everyday care"
          railLabel="top-selling health essentials"
        />
      </section>
    </main>
  );
}
