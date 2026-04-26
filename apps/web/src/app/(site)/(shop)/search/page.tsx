import { fetchCatalogProducts, type ApiCatalogProductSummary } from "@/lib/api";
import { SearchExperience } from "@/components/search-experience";
import { searchSuggestions, storefrontProducts } from "@/lib/storefront-data";

const substituteTags = ["Same salt", "Best savings", "Prescription required", "In stock"];

type SearchPageProduct = {
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

function formatPrice(value: string) {
  const amount = Number.parseFloat(value);

  if (Number.isNaN(amount)) {
    return value;
  }

  return Number.isInteger(amount) ? String(amount) : amount.toFixed(2);
}

function discountFromPrices(mrp: string, salePrice: string) {
  const mrpValue = Number.parseFloat(mrp);
  const saleValue = Number.parseFloat(salePrice);

  if (Number.isNaN(mrpValue) || Number.isNaN(saleValue) || mrpValue <= 0 || saleValue >= mrpValue) {
    return "0% OFF";
  }

  return `${Math.round(((mrpValue - saleValue) / mrpValue) * 100)}% OFF`;
}

function fallbackSearchProducts() {
  return storefrontProducts.map((product) => ({
    ...product,
    tags: product.tags.map((tag) => (tag === "Prescription only" ? "Prescription required" : tag))
  }));
}

function buildLiveSearchProducts(products: ApiCatalogProductSummary[]): SearchPageProduct[] {
  const compositionCounts = products.reduce<Record<string, number>>((accumulator, product) => {
    const key = product.composition.trim().toLowerCase();

    if (!key) {
      return accumulator;
    }

    accumulator[key] = (accumulator[key] ?? 0) + 1;
    return accumulator;
  }, {});

  return products.map((product) => {
    const compositionKey = product.composition.trim().toLowerCase();
    const tags = new Set<string>();

    if (compositionKey && (compositionCounts[compositionKey] ?? 0) > 1) {
      tags.add("Same salt");
    }
    if (discountFromPrices(product.mrp, product.sale_price) !== "0% OFF") {
      tags.add("Best savings");
    }
    if (product.requires_prescription) {
      tags.add("Prescription required");
    }
    if (product.stock_status !== "out_of_stock") {
      tags.add("In stock");
    }

    return {
      slug: product.slug,
      name: product.name,
      off: discountFromPrices(product.mrp, product.sale_price),
      mrp: formatPrice(product.mrp),
      price: formatPrice(product.sale_price),
      brand: product.brand?.name ?? product.manufacturer ?? "TrueCare",
      salt: product.composition || product.brand?.name || "General composition",
      tags: Array.from(tags),
      meta: `${product.manufacturer || product.brand?.name || "TrueCare"} | ${product.pack_size || "Pack details"}`,
      rx: product.requires_prescription
    };
  });
}

function buildLiveSuggestions(products: SearchPageProduct[]) {
  const candidates = new Set<string>();

  for (const product of products) {
    candidates.add(product.name.toLowerCase());
    candidates.add(product.brand.toLowerCase());
    candidates.add(product.salt.toLowerCase());
  }

  return Array.from(candidates)
    .filter(Boolean)
    .slice(0, 10);
}

export default async function SearchPage({
  searchParams
}: {
  searchParams?: Promise<{ q?: string }>;
}) {
  const resolvedSearchParams = searchParams ? await searchParams : undefined;
  const initialQuery = resolvedSearchParams?.q?.trim() ?? "";
  let interactiveProducts: SearchPageProduct[] = initialQuery ? [] : fallbackSearchProducts();
  let popularSearches: string[] = [...searchSuggestions];

  try {
    const liveProducts = await fetchCatalogProducts(initialQuery ? { q: initialQuery } : {});

    if (liveProducts.length > 0) {
      interactiveProducts = buildLiveSearchProducts(liveProducts);
      const liveSuggestions = buildLiveSuggestions(interactiveProducts);

      if (liveSuggestions.length > 0) {
        popularSearches = liveSuggestions;
      }
    }
  } catch {
    interactiveProducts = initialQuery ? [] : fallbackSearchProducts();
  }

  return (
    <SearchExperience
      products={interactiveProducts}
      popularSearches={popularSearches}
      substituteTags={substituteTags}
      initialQuery={initialQuery}
    />
  );
}
