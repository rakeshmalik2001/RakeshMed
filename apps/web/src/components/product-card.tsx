import Link from "next/link";
import type { CSSProperties } from "react";

import { AddToCartButton } from "@/components/add-to-cart-button";

type ProductCardProps = {
  slug?: string;
  name: string;
  off: string;
  mrp: string;
  price: string;
  meta?: string;
  rx?: boolean;
  note?: string;
};

function toSlug(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function getVisualTheme(name: string) {
  const themes = [
    { shell: "linear-gradient(180deg, #eff7ff 0%, #d9ebff 100%)", band: "#2f80ed", ink: "#1f416c" },
    { shell: "linear-gradient(180deg, #f2fff7 0%, #daf5e7 100%)", band: "#13a46b", ink: "#1f5a49" },
    { shell: "linear-gradient(180deg, #fff7ef 0%, #ffe4cc 100%)", band: "#f38b2a", ink: "#7b4f1c" },
    { shell: "linear-gradient(180deg, #f6f3ff 0%, #e5ddff 100%)", band: "#7a5af8", ink: "#49389f" }
  ] as const;
  const seed = name.split("").reduce((sum, char) => sum + char.charCodeAt(0), 0);

  return themes[seed % themes.length];
}

export function ProductCard({
  slug,
  name,
  off,
  mrp,
  price,
  meta = "Medicine pack",
  rx = false,
  note = "Save more with substitute"
}: ProductCardProps) {
  const productSlug = slug ?? toSlug(name);
  const visualTheme = getVisualTheme(name);
  const initials = name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  return (
    <article className="product-card">
      <span className="product-badge">{off}</span>
      <div className="product-image" style={{ "--product-shell": visualTheme.shell, "--product-band": visualTheme.band } as CSSProperties}>
        <div className="product-packshot">
          <span className="product-packshot-band" />
          <span className="product-packshot-copy">TrueCare</span>
          <strong style={{ color: visualTheme.ink }}>{initials}</strong>
          <small>{meta.split("|")[0]?.trim() ?? "Care item"}</small>
        </div>
        <span className="product-pack-pill" />
      </div>
      <div className="product-copy">
        <p className="product-meta">{meta}</p>
        <h3>
          <Link href={`/medicine/${productSlug}`} className="product-name-link">
            {name}
          </Link>
        </h3>
        <div className="price-line">
          <span className="mrp">
            MRP <del>Rs. {mrp}</del>
          </span>
        </div>
        <div className="product-actions">
          <div className="product-price-stack">
            <span className="price">Rs. {price}</span>
            <span className="product-unit-price">Best price</span>
          </div>
          <AddToCartButton product={{ slug: productSlug, name, off, mrp, price, meta, rx }} />
        </div>
      </div>
      <div className="substitute-note">{note}</div>
    </article>
  );
}
