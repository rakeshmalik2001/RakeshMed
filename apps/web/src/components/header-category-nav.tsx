"use client";

import { useEffect, useState, type CSSProperties, type FocusEvent, type MouseEvent } from "react";
import type { Route } from "next";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FiChevronRight } from "react-icons/fi";

import { getNavIcon } from "@/components/nav-icons";
import { fetchCatalogCategories } from "@/lib/api";
import { buildNavCatalog, type NavCategory } from "@/lib/nav-catalog";

function dropdownAlignment(index: number, total: number) {
  if (index === 0) {
    return "align-left";
  }

  if (index >= total - 2) {
    return "align-right";
  }

  return "align-center";
}

export function HeaderCategoryNav() {
  const pathname = usePathname();
  const [categories, setCategories] = useState<NavCategory[]>([]);
  const [activeSubcategoryByCategory, setActiveSubcategoryByCategory] = useState<Record<number, string>>({});

  useEffect(() => {
    let isMounted = true;

    void fetchCatalogCategories()
      .then((items) => {
        if (isMounted) {
          setCategories(buildNavCatalog(items));
        }
      })
      .catch(() => {
        if (isMounted) {
          setCategories([]);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  if (categories.length === 0) {
    return null;
  }

  return (
    <nav className="category-strip mega-nav">
      {categories.map((category, index) => {
        const CategoryIcon = getNavIcon(category.iconKey);
        const isRouteActive = pathname.startsWith(category.href);
        const hasSubcategories = (category.subcategories?.length ?? 0) > 0;
        const hasLeafItems = (category.subcategories ?? []).some((subcategory) => subcategory.items.length > 0);
        const selectedSubcategoryLabel =
          activeSubcategoryByCategory[category.id] ?? category.subcategories?.[0]?.label ?? "";
        const selectedSubcategory =
          category.subcategories?.find((subcategory) => subcategory.label === selectedSubcategoryLabel) ??
          category.subcategories?.[0];
        const activateSubcategory = (label?: string) => {
          if (!label || label === activeSubcategoryByCategory[category.id]) {
            return;
          }

          setActiveSubcategoryByCategory((current) => ({ ...current, [category.id]: label }));
        };

        const handleSubcategoryHover = (event: MouseEvent<HTMLDivElement>) => {
          const hoveredCategory = (event.target as HTMLElement)
            .closest<HTMLElement>("[data-subcategory]")
            ?.dataset.subcategory;

          activateSubcategory(hoveredCategory);
        };

        const handleSubcategoryFocus = (event: FocusEvent<HTMLDivElement>) => {
          const focusedCategory = (event.target as HTMLElement)
            .closest<HTMLElement>("[data-subcategory]")
            ?.dataset.subcategory;

          activateSubcategory(focusedCategory);
        };

        return (
          <div key={category.id} className={`mega-nav-item${isRouteActive ? " route-active" : ""}`}>
            <Link
              href={category.href as Route}
              className="mega-nav-trigger"
              style={
                {
                  "--category-accent": category.accent,
                  "--category-soft": category.soft,
                  "--category-border": category.border
                } as CSSProperties
              }
            >
              <span className="mega-nav-trigger-icon">
                <CategoryIcon />
              </span>
              <span>{category.label}</span>
            </Link>

            {hasSubcategories ? (
              <div
                className={`mega-dropdown ${hasLeafItems ? "mega-dropdown-mega" : "mega-dropdown-simple"} ${dropdownAlignment(index, categories.length)}`}
                style={
                  {
                    "--category-accent": category.accent,
                    "--category-soft": category.soft,
                    "--category-border": category.border
                  } as CSSProperties
                }
              >
                {hasLeafItems ? (
                  <>
                    <div
                      className="mega-dropdown-subcategories"
                      onMouseOver={handleSubcategoryHover}
                      onMouseMove={handleSubcategoryHover}
                      onFocusCapture={handleSubcategoryFocus}
                    >
                      {category.subcategories?.map((subcategory) => {
                        const SubcategoryIcon = getNavIcon(subcategory.iconKey);
                        const isSubcategoryActive = selectedSubcategory?.id === subcategory.id;

                        return (
                          <button
                            key={subcategory.id}
                            type="button"
                            className={`mega-subcategory-link${isSubcategoryActive ? " active" : ""}`}
                            onMouseEnter={() => activateSubcategory(subcategory.label)}
                            onPointerEnter={() => activateSubcategory(subcategory.label)}
                            onFocus={() => activateSubcategory(subcategory.label)}
                            data-subcategory={subcategory.label}
                          >
                            <span className="mega-subcategory-copy">
                              <span className="mega-subcategory-icon">
                                <SubcategoryIcon />
                              </span>
                              <span>{subcategory.label}</span>
                            </span>
                            <FiChevronRight />
                          </button>
                        );
                      })}
                    </div>

                    <div className="mega-dropdown-content">
                      <div className="mega-dropdown-content-head">
                        <span className="mega-content-kicker">Shop by {selectedSubcategory?.label ?? category.label}</span>
                        <Link href={(selectedSubcategory?.href ?? category.href) as Route} className="mega-content-link">
                          View all
                        </Link>
                      </div>

                      <div className="mega-leaf-grid">
                        {selectedSubcategory?.items.map((item) => {
                          const LeafIcon = getNavIcon(item.iconKey);

                          return (
                            <Link
                              key={item.id}
                              href={item.href as Route}
                              className={`mega-leaf-link${pathname.startsWith(item.href) ? " active" : ""}`}
                            >
                              <span className="mega-leaf-copy">
                                <span className="mega-leaf-icon">
                                  <LeafIcon />
                                </span>
                                <span>{item.label}</span>
                              </span>
                            </Link>
                          );
                        })}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="mega-dropdown-content">
                    <div className="mega-dropdown-content-head">
                      <span className="mega-content-kicker">Shop by {category.label}</span>
                      <Link href={category.href as Route} className="mega-content-link">
                        View all
                      </Link>
                    </div>

                    <div className="mega-dropdown-simple-list">
                      {category.subcategories?.map((subcategory) => {
                        const SubcategoryIcon = getNavIcon(subcategory.iconKey);
                        const isSubcategoryActive = pathname.startsWith(subcategory.href);

                        return (
                          <Link
                            key={subcategory.id}
                            href={subcategory.href as Route}
                            className={`mega-leaf-link simple${isSubcategoryActive ? " active" : ""}`}
                          >
                            <span className="mega-leaf-copy">
                              <span className="mega-leaf-icon">
                                <SubcategoryIcon />
                              </span>
                              <span>{subcategory.label}</span>
                            </span>
                            <FiChevronRight />
                          </Link>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        );
      })}
    </nav>
  );
}
