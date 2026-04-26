"use client";

import Link from "next/link";
import { startTransition, useMemo, useState } from "react";

import { ProductCard } from "@/components/product-card";

type CategoryProduct = {
  slug?: string;
  name: string;
  off: string;
  mrp: string;
  price: string;
  brand: string;
  form: string;
  useFor: string;
  tags: string[];
  meta?: string;
  rx?: boolean;
};

type CategoryBrowserProps = {
  products: CategoryProduct[];
  filters: {
    brands: string[];
    form: string[];
    useFor: string[];
  };
};

export function CategoryBrowser({ products, filters }: CategoryBrowserProps) {
  const [selectedBrands, setSelectedBrands] = useState<string[]>([]);
  const [selectedForms, setSelectedForms] = useState<string[]>([]);
  const [selectedUses, setSelectedUses] = useState<string[]>([]);
  const [selectedQuickTag, setSelectedQuickTag] = useState<string>("All");
  const [sort, setSort] = useState<"popularity" | "priceLow">("popularity");

  const filteredProducts = useMemo(() => {
    let next = products.filter((product) => {
      const matchesBrand =
        selectedBrands.length === 0 || selectedBrands.includes(product.brand);
      const matchesForm =
        selectedForms.length === 0 || selectedForms.includes(product.form);
      const matchesUse =
        selectedUses.length === 0 || selectedUses.includes(product.useFor);
      const matchesTag =
        selectedQuickTag === "All" || product.tags.includes(selectedQuickTag);

      return matchesBrand && matchesForm && matchesUse && matchesTag;
    });

    if (sort === "priceLow") {
      next = [...next].sort((a, b) => Number(a.price) - Number(b.price));
    }

    return next;
  }, [products, selectedBrands, selectedForms, selectedQuickTag, selectedUses, sort]);

  function toggleItem(
    value: string,
    items: string[],
    setter: (next: string[]) => void
  ) {
    startTransition(() => {
      setter(items.includes(value) ? items.filter((item) => item !== value) : [...items, value]);
    });
  }

  return (
    <>
      <div className="catalog-toolbar">
        <div className="catalog-chips">
          {["All", "Prescription only", "In stock", "Best savings"].map((item) => (
            <button
              key={item}
              type="button"
              className={`catalog-chip-button ${selectedQuickTag === item ? "active" : ""}`}
              onClick={() => setSelectedQuickTag(item)}
            >
              {item}
            </button>
          ))}
        </div>
        <div className="sort-toggle-row">
          <button
            type="button"
            className={`catalog-chip-button ${sort === "popularity" ? "active" : ""}`}
            onClick={() => setSort("popularity")}
          >
            Popularity
          </button>
          <button
            type="button"
            className={`catalog-chip-button ${sort === "priceLow" ? "active" : ""}`}
            onClick={() => setSort("priceLow")}
          >
            Price Low to High
          </button>
        </div>
      </div>

      <section className="catalog-layout">
        <aside className="filter-panel">
          <div className="filter-group">
            <h3>Brands</h3>
            {filters.brands.map((item) => (
              <label key={item} className="filter-option">
                <input
                  type="checkbox"
                  checked={selectedBrands.includes(item)}
                  onChange={() => toggleItem(item, selectedBrands, setSelectedBrands)}
                />{" "}
                {item}
              </label>
            ))}
          </div>
          <div className="filter-group">
            <h3>Dosage Form</h3>
            {filters.form.map((item) => (
              <label key={item} className="filter-option">
                <input
                  type="checkbox"
                  checked={selectedForms.includes(item)}
                  onChange={() => toggleItem(item, selectedForms, setSelectedForms)}
                />{" "}
                {item}
              </label>
            ))}
          </div>
          <div className="filter-group">
            <h3>Use For</h3>
            {filters.useFor.map((item) => (
              <label key={item} className="filter-option">
                <input
                  type="checkbox"
                  checked={selectedUses.includes(item)}
                  onChange={() => toggleItem(item, selectedUses, setSelectedUses)}
                />{" "}
                {item}
              </label>
            ))}
          </div>
          <div className="filter-group">
            <button
              type="button"
              className="secondary-action"
              onClick={() => {
                setSelectedBrands([]);
                setSelectedForms([]);
                setSelectedUses([]);
                setSelectedQuickTag("All");
                setSort("popularity");
              }}
            >
              Reset filters
            </button>
          </div>
        </aside>

        <div className="catalog-results">
          <div className="results-summary">
            <strong>Showing {filteredProducts.length} medicines</strong>
            <span>Filters update product count instantly.</span>
          </div>

          <div className="catalog-grid">
            {filteredProducts.map((product) => (
              <ProductCard
                key={product.slug ?? product.name}
                slug={product.slug}
                name={product.name}
                off={product.off}
                mrp={product.mrp}
                price={product.price}
                meta={product.meta}
                rx={product.rx}
              />
            ))}
          </div>

          <div className="seo-info-box">
            <h2>About heart care medicines</h2>
            <p>
              This category layout is ready for SEO copy, FAQs, medical disclaimers, and internal
              links to brand, salt, and substitute pages.
            </p>
            <Link href="/upload-prescription" className="section-link">
              Upload prescription for pharmacist help
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
