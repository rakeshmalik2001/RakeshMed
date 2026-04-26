"use client";

import { useState, type CSSProperties } from "react";
import type { Route } from "next";
import Link from "next/link";

import { getNavIcon } from "@/components/nav-icons";
import type { NavCategory } from "@/lib/nav-catalog";

type HomepageCategoryShowcaseProps = {
  categories: NavCategory[];
};

export function HomepageCategoryShowcase({
  categories
}: HomepageCategoryShowcaseProps) {
  const [activeCategory, setActiveCategory] = useState(categories[0]?.label ?? "");
  const activeCategorySection =
    categories.find((section) => section.label === activeCategory) ?? categories[0];
  const activeCategoryCards =
    activeCategorySection?.variant === "mega"
      ? activeCategorySection.subcategories?.map((subcategory) => ({
          label: subcategory.label,
          href: subcategory.href,
          iconKey: subcategory.iconKey
        })) ?? []
      : activeCategorySection?.items?.slice(0, 6).map((item) => ({
          label: item.label,
          href: item.href,
          iconKey: item.iconKey
        })) ?? [];

  if (!activeCategorySection) {
    return null;
  }

  return (
    <div
      className="category-showcase"
      style={
        {
          "--active-category-soft": activeCategorySection.soft,
          "--active-category-border": activeCategorySection.border,
          "--active-category-accent": activeCategorySection.accent
        } as CSSProperties
      }
    >
      <aside className="category-menu">
        {categories.map((section) => {
          const SectionIcon = getNavIcon(section.iconKey);

          return (
            <button
              key={section.label}
              type="button"
              className={`category-menu-item ${activeCategory === section.label ? "active" : ""}`}
              onMouseEnter={() => setActiveCategory(section.label)}
              onFocus={() => setActiveCategory(section.label)}
              style={
                {
                  "--menu-item-soft": section.soft,
                  "--menu-item-accent": section.accent,
                  "--menu-item-border": section.border
                } as CSSProperties
              }
            >
              <span className="category-menu-icon">
                <SectionIcon />
              </span>
              <span className="category-menu-label">{section.label}</span>
            </button>
          );
        })}
      </aside>

      <div className="category-grid-panel">
        <div
          className={`category-grid ${activeCategorySection.variant === "simple" ? "category-grid-simple" : ""}`}
        >
          {activeCategoryCards.map((category) => {
            const CategoryCardIcon = getNavIcon(category.iconKey);

            return (
              <Link
                key={category.label}
                href={category.href as Route}
                className="category-card"
              >
                <h3>{category.label}</h3>
                <div className="category-illustration">
                  <span className="category-illustration-icon">
                    <CategoryCardIcon />
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
