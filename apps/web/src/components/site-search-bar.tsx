"use client";

import { useEffect, useMemo, useState } from "react";
import { FiChevronDown, FiMapPin, FiSearch } from "react-icons/fi";

type SiteSearchBarProps = {
  query?: string;
  className?: string;
  showButtonLabel?: boolean;
  animatedTerms?: readonly string[];
  action?: string;
  locationLabel?: string;
};

export function SiteSearchBar({
  query,
  className = "",
  showButtonLabel = true,
  animatedTerms,
  action = "/search",
  locationLabel = "Deliver to Mumbai"
}: SiteSearchBarProps) {
  const [value, setValue] = useState(query ?? "");
  const [rotatingIndex, setRotatingIndex] = useState(0);

  useEffect(() => {
    if (typeof query === "string") {
      setValue(query);
      return;
    }

    const currentQuery = new URLSearchParams(window.location.search).get("q") ?? "";
    setValue(currentQuery);
  }, [query]);

  useEffect(() => {
    if (!animatedTerms?.length || value.trim().length > 0) {
      return;
    }

    const interval = window.setInterval(() => {
      setRotatingIndex((current) => (current + 1) % animatedTerms.length);
    }, 2000);

    return () => window.clearInterval(interval);
  }, [animatedTerms, value]);

  const placeholder = useMemo(() => {
    if (!animatedTerms?.length) {
      return "Search by medicine, salt, or brand";
    }

    return `Search for ${animatedTerms[rotatingIndex]}`;
  }, [animatedTerms, rotatingIndex]);

  return (
    <form action={action} className={`search-shell ${className}`.trim()}>
      <button type="button" className="location-pill" data-testid="site-search-location-button">
        <FiMapPin />
        <span>{locationLabel}</span>
        <FiChevronDown />
      </button>
      <div className="search-input">
        <FiSearch className="search-leading-icon" />
        <input
          type="search"
          name="q"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          className="search-input-control"
          placeholder={placeholder}
          aria-label="Search medicines, salts, or brands"
          data-testid="site-search-input"
        />
      </div>
      <button type="submit" className="search-submit" data-testid="site-search-submit">
        <FiSearch />
        {showButtonLabel ? <span>Search</span> : null}
      </button>
    </form>
  );
}
