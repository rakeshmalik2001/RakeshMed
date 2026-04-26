"use client";

import { useEffect, useRef, useState } from "react";

import { ProductCard } from "@/components/product-card";
import type { StorefrontProduct } from "@/lib/storefront-data";

type ProductRailCarouselProps = {
  products: StorefrontProduct[];
  note: string;
  railLabel: string;
};

function RailArrow({ direction }: { direction: "left" | "right" }) {
  return (
    <span aria-hidden="true" className="product-rail-arrow">
      {direction === "left" ? "‹" : "›"}
    </span>
  );
}

export function ProductRailCarousel({
  products,
  note,
  railLabel
}: ProductRailCarouselProps) {
  const railRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(true);

  function updateScrollState() {
    if (!railRef.current) {
      return;
    }

    const { scrollLeft, scrollWidth, clientWidth } = railRef.current;
    const maxScrollLeft = Math.max(0, scrollWidth - clientWidth);
    const epsilon = 4;

    setCanScrollLeft(scrollLeft > epsilon);
    setCanScrollRight(scrollLeft < maxScrollLeft - epsilon);
  }

  useEffect(() => {
    updateScrollState();

    const rail = railRef.current;
    if (!rail) {
      return;
    }

    rail.addEventListener("scroll", updateScrollState, { passive: true });
    window.addEventListener("resize", updateScrollState);

    return () => {
      rail.removeEventListener("scroll", updateScrollState);
      window.removeEventListener("resize", updateScrollState);
    };
  }, [products.length]);

  function scrollRail(direction: "left" | "right") {
    if (!railRef.current) {
      return;
    }

    railRef.current.scrollBy({
      left: direction === "right" ? 900 : -900,
      behavior: "smooth"
    });
  }

  return (
    <div className="product-rail-shell">
      {canScrollLeft ? (
        <button
          type="button"
          className="product-rail-control product-rail-control-left"
          aria-label={`Scroll ${railLabel} left`}
          onClick={() => scrollRail("left")}
        >
          <RailArrow direction="left" />
        </button>
      ) : null}

      <div ref={railRef} className="product-rail">
        {products.map((product, index) => (
          <ProductCard
            key={`${railLabel}-${product.slug}-${index}`}
            slug={product.slug}
            name={product.name}
            off={product.off}
            mrp={product.mrp}
            price={product.price}
            meta={product.meta}
            rx={product.rx}
            note={note}
          />
        ))}
      </div>

      {canScrollRight ? (
        <button
          type="button"
          className="product-rail-control product-rail-control-right"
          aria-label={`Scroll ${railLabel} right`}
          onClick={() => scrollRail("right")}
        >
          <RailArrow direction="right" />
        </button>
      ) : null}
    </div>
  );
}
