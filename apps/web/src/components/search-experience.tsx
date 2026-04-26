"use client";

import Link from "next/link";
import { FiArrowRight, FiSearch } from "react-icons/fi";
import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";

import { ProductCard } from "@/components/product-card";

type SearchProduct = {
  slug?: string;
  name: string;
  off: string;
  mrp: string;
  price: string;
  brand: string;
  salt: string;
  tags: string[];
  meta?: string;
  rx?: boolean;
};

type SearchExperienceProps = {
  products: SearchProduct[];
  popularSearches: string[];
  substituteTags: string[];
  initialQuery?: string;
};

export function SearchExperience({
  products,
  popularSearches,
  substituteTags,
  initialQuery = ""
}: SearchExperienceProps) {
  const [query, setQuery] = useState(initialQuery);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedBrands, setSelectedBrands] = useState<string[]>([]);
  const [selectedSalts, setSelectedSalts] = useState<string[]>([]);
  const [sort, setSort] = useState<"relevance" | "priceLow">("relevance");

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  const deferredQuery = useDeferredValue(query);
  const normalizedQuery = deferredQuery.trim().toLowerCase();

  const brands = useMemo(
    () => Array.from(new Set(products.map((product) => product.brand))),
    [products]
  );
  const salts = useMemo(
    () => Array.from(new Set(products.map((product) => product.salt))),
    [products]
  );

  const filteredProducts = useMemo(() => {
    let next = products.filter((product) => {
      const matchesQuery =
        normalizedQuery.length === 0 ||
        product.name.toLowerCase().includes(normalizedQuery) ||
        product.brand.toLowerCase().includes(normalizedQuery) ||
        product.salt.toLowerCase().includes(normalizedQuery);

      const matchesTags =
        selectedTags.length === 0 ||
        selectedTags.every((tag) => product.tags.includes(tag));

      const matchesBrands =
        selectedBrands.length === 0 || selectedBrands.includes(product.brand);

      const matchesSalts =
        selectedSalts.length === 0 || selectedSalts.includes(product.salt);

      return matchesQuery && matchesTags && matchesBrands && matchesSalts;
    });

    if (sort === "priceLow") {
      next = [...next].sort((a, b) => Number(a.price) - Number(b.price));
    }

    return next;
  }, [normalizedQuery, products, selectedBrands, selectedSalts, selectedTags, sort]);

  const exactMatches = useMemo(
    () =>
      filteredProducts.filter((product) => {
        if (normalizedQuery.length === 0) {
          return true;
        }

        const name = product.name.toLowerCase();
        const brand = product.brand.toLowerCase();
        const salt = product.salt.toLowerCase();

        return (
          name === normalizedQuery ||
          name.startsWith(normalizedQuery) ||
          brand === normalizedQuery ||
          salt === normalizedQuery
        );
      }),
    [filteredProducts, normalizedQuery]
  );

  const sameSaltOptions = useMemo(() => {
    const exactSalts = new Set(exactMatches.map((product) => product.salt));

    return filteredProducts.filter(
      (product) =>
        !exactMatches.includes(product) && exactSalts.size > 0 && exactSalts.has(product.salt)
    );
  }, [exactMatches, filteredProducts]);

  const relatedResults = useMemo(
    () => filteredProducts.filter((product) => !exactMatches.includes(product) && !sameSaltOptions.includes(product)),
    [exactMatches, filteredProducts, sameSaltOptions]
  );

  const suggestedSearches = useMemo(() => {
    if (normalizedQuery.length === 0) {
      return popularSearches.slice(0, 4);
    }

    return popularSearches
      .filter((term) => term.toLowerCase().includes(normalizedQuery) && term.toLowerCase() !== normalizedQuery)
      .slice(0, 4);
  }, [normalizedQuery, popularSearches]);

  function toggleItem(
    value: string,
    items: string[],
    setter: (next: string[]) => void
  ) {
    startTransition(() => {
      setter(items.includes(value) ? items.filter((item) => item !== value) : [...items, value]);
    });
  }

  function resetSearchExperience(nextQuery = initialQuery) {
    startTransition(() => {
      setQuery(nextQuery);
      setSelectedTags([]);
      setSelectedBrands([]);
      setSelectedSalts([]);
      setSort("relevance");
    });
  }

  const searchHeading = query.trim() || initialQuery.trim() || "medicine";

  function ResultSection({
    title,
    description,
    products: sectionProducts
  }: {
    title: string;
    description: string;
    products: SearchProduct[];
  }) {
    if (sectionProducts.length === 0) {
      return null;
    }

    return (
      <section className="search-result-section">
        <div className="search-result-section-head">
          <div>
            <h2>{title}</h2>
            <p>{description}</p>
          </div>
          <span className="search-result-count">{sectionProducts.length}</span>
        </div>
        <div className="search-results-grid">
          {sectionProducts.map((product) => (
            <ProductCard
              key={`${title}-${product.slug ?? product.name}`}
              slug={product.slug}
              name={product.name}
              off={product.off}
              mrp={product.mrp}
              price={product.price}
              meta={product.meta}
              rx={product.rx}
              note="Compare substitutes and savings"
            />
          ))}
        </div>
      </section>
    );
  }

  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Search</div>

      <section className="search-hero">
        <div>
          <p className="eyebrow">Medicine Search</p>
          <h1>Results for {searchHeading.toUpperCase()}</h1>
          <p>
            Search by medicine, salt, or brand and compare substitutes with quick price visibility.
          </p>
        </div>
        <div className="search-hero-meta">
          <strong>{filteredProducts.length} matching medicines</strong>
          <span>Use filters to narrow down same-salt options and lower-cost substitutes.</span>
        </div>
      </section>

        <div className="search-live-box">
          <div className="search-live-input-wrap">
            <span className="search-live-icon">
              <FiSearch />
            </span>
            <input
              className="search-live-input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by medicine, salt, or brand"
            />
          </div>
          <button type="button" className="secondary-action" onClick={() => resetSearchExperience()}>
            Reset filters
          </button>
        </div>

      <div className="search-top-tools">
        <div className="search-chip-row">
          {popularSearches.map((term) => (
            <button
              key={term}
              type="button"
              className={`catalog-chip-button ${query === term ? "active" : ""}`}
              onClick={() => setQuery(term)}
            >
              {term}
            </button>
          ))}
        </div>
        <div className="sort-toggle-row">
          <button
            type="button"
            className={`catalog-chip-button ${sort === "relevance" ? "active" : ""}`}
            onClick={() => setSort("relevance")}
          >
            Relevance
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

      <section className="search-layout">
        <aside className="filter-panel search-filter-panel">
          <div className="filter-group">
            <h3>Popular filters</h3>
            {substituteTags.map((item) => (
              <label key={item} className="filter-option">
                <input
                  type="checkbox"
                  checked={selectedTags.includes(item)}
                  onChange={() => toggleItem(item, selectedTags, setSelectedTags)}
                />{" "}
                {item}
              </label>
            ))}
          </div>

          <div className="filter-group">
            <h3>Brand</h3>
            {brands.map((item) => (
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
            <h3>Salt composition</h3>
            {salts.map((item) => (
              <label key={item} className="filter-option">
                <input
                  type="checkbox"
                  checked={selectedSalts.includes(item)}
                  onChange={() => toggleItem(item, selectedSalts, setSelectedSalts)}
                />{" "}
                {item}
              </label>
            ))}
          </div>
        </aside>

        <div className="search-results-column">
          <div className="search-helper-card">
            <div>
              <strong>Want cheaper alternatives?</strong>
              <p>Compare same-salt medicines and ask our pharmacists before placing the order.</p>
            </div>
            <Link href="/upload-prescription" className="secondary-action">
              Upload prescription
            </Link>
          </div>

          {suggestedSearches.length > 0 ? (
            <div className="search-suggestion-card">
              <strong>Suggested searches</strong>
              <div className="search-chip-row">
                {suggestedSearches.map((term) => (
                  <button key={term} type="button" className="catalog-chip-button" onClick={() => setQuery(term)}>
                    {term}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {selectedTags.length > 0 || selectedBrands.length > 0 || selectedSalts.length > 0 ? (
            <div className="search-active-filters">
              {selectedTags.map((item) => (
                <button key={item} type="button" className="search-active-filter" onClick={() => toggleItem(item, selectedTags, setSelectedTags)}>
                  {item} x
                </button>
              ))}
              {selectedBrands.map((item) => (
                <button key={item} type="button" className="search-active-filter" onClick={() => toggleItem(item, selectedBrands, setSelectedBrands)}>
                  {item} x
                </button>
              ))}
              {selectedSalts.map((item) => (
                <button key={item} type="button" className="search-active-filter" onClick={() => toggleItem(item, selectedSalts, setSelectedSalts)}>
                  {item} x
                </button>
              ))}
            </div>
          ) : null}

          <div className="results-summary">
            <strong>Showing {filteredProducts.length} results</strong>
            <span>
              {exactMatches.length > 0
                ? `${exactMatches.length} exact or strongest matches found first.`
                : "Live results update as you type or change filters."}
            </span>
          </div>

          <ResultSection
            title={normalizedQuery.length > 0 ? "Best matches" : "Popular results"}
            description={
              normalizedQuery.length > 0
                ? "Products that most closely match your search by medicine name, brand, or salt."
                : "A quick starting set based on the current catalog."
            }
            products={exactMatches}
          />

          <ResultSection
            title="Same-salt options"
            description="Alternatives with the same salt composition, useful when you want to compare savings."
            products={sameSaltOptions}
          />

          <ResultSection
            title="Related results"
            description="Other relevant products that match your filters or search more broadly."
            products={relatedResults}
          />

          {filteredProducts.length === 0 ? (
            <div className="zero-state-card">
              <div>
                <h2>Not finding your medicine?</h2>
                <p>
                  Try searching by salt composition or upload your prescription for pharmacist-assisted
                  matching and substitute suggestions.
                </p>
                <div className="zero-state-hints">
                  {popularSearches.slice(0, 3).map((term) => (
                    <button key={term} type="button" className="zero-state-link" onClick={() => resetSearchExperience(term)}>
                      Try {term}
                      <FiArrowRight />
                    </button>
                  ))}
                </div>
              </div>
              <div className="success-actions">
                <Link href="/upload-prescription" className="primary-action">
                  Upload prescription
                </Link>
                <button type="button" className="secondary-action" onClick={() => resetSearchExperience(popularSearches[0] ?? "")}>
                  Reset search
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </main>
  );
}
