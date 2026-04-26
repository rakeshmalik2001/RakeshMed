import { fetchCatalogCategories, fetchCatalogProducts, type ApiCatalogProductSummary } from "@/lib/api";
import { buildNavCatalog, type NavCategory, type NavSubcategory } from "@/lib/nav-catalog";

type CategoryPageLink = {
  label: string;
  href: string;
  active: boolean;
};

type CategoryPageProduct = {
  slug: string;
  name: string;
  off: string;
  mrp: string;
  price: string;
  brand: string;
  accent: string;
};

export type ResolvedCategoryPage = {
  breadcrumbs: Array<{ label: string; href?: string }>;
  title: string;
  categoryOptions: CategoryPageLink[];
  subcategoryOptions: CategoryPageLink[];
  brandOptions: string[];
  products: CategoryPageProduct[];
  content: Array<{
    heading: string;
    intro?: string;
    bullets: string[];
    outro?: string;
  }>;
  faqs: Array<{
    question: string;
    answer: string;
  }>;
};

const accentPalette = [
  "#f4f0ff",
  "#eff8ff",
  "#fff4f1",
  "#f5f6f8",
  "#faf3ef",
  "#fff7e8",
  "#fffce8",
  "#fff5f0",
  "#effcff",
  "#fcfbf5",
  "#fbffe9",
  "#f3fbff"
];

export function toProductSlug(name: string) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function accentFromValue(value: string) {
  const sum = value.split("").reduce((accumulator, character) => accumulator + character.charCodeAt(0), 0);
  return accentPalette[sum % accentPalette.length];
}

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

function mapApiProductsToCategoryProducts(products: ApiCatalogProductSummary[]): CategoryPageProduct[] {
  return products.map((product) => ({
    slug: product.slug,
    name: product.name,
    off: discountFromPrices(product.mrp, product.sale_price),
    mrp: formatPrice(product.mrp),
    price: formatPrice(product.sale_price),
    brand: product.brand?.name ?? product.manufacturer ?? "TrueCare",
    accent: accentFromValue(product.slug)
  }));
}

function formatTitle(value: string) {
  return value
    .split("-")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function normalizeSearchValue(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function matchesItemSlug(product: ApiCatalogProductSummary, itemSlug: string) {
  const itemLabel = normalizeSearchValue(formatTitle(itemSlug));
  if (!itemLabel) {
    return true;
  }

  const haystack = normalizeSearchValue(
    [
      product.name,
      product.composition,
      product.manufacturer,
      product.brand?.name ?? "",
      product.category.name
    ].join(" ")
  );

  return itemLabel.split(" ").every((part) => haystack.includes(part));
}

function uniqueProducts(products: ApiCatalogProductSummary[]) {
  const map = new Map<string, ApiCatalogProductSummary>();

  for (const product of products) {
    map.set(product.slug, product);
  }

  return Array.from(map.values());
}

function buildContent(title: string, products: CategoryPageProduct[], brandOptions: string[]) {
  const label = title.replace(/ Products$/, "");
  const lowerLabel = label.toLowerCase();
  const featuredBrands = brandOptions.slice(0, 3).join(", ");
  const priceFloor = products.reduce<number | null>((lowest, product) => {
    const price = Number.parseFloat(product.price);

    if (Number.isNaN(price)) {
      return lowest;
    }

    return lowest === null ? price : Math.min(lowest, price);
  }, null);
  const priceCeiling = products.reduce<number | null>((highest, product) => {
    const price = Number.parseFloat(product.price);

    if (Number.isNaN(price)) {
      return highest;
    }

    return highest === null ? price : Math.max(highest, price);
  }, null);
  const priceSummary =
    priceFloor !== null && priceCeiling !== null
      ? `Current collection prices range from Rs. ${priceFloor.toFixed(2)} to Rs. ${priceCeiling.toFixed(2)}.`
      : "Current collection prices update from the available catalog selection.";

  return [
    {
      heading: `Benefits of ${label}`,
      intro: `${label} collections make it easier to compare trusted brands, pack sizes, and routine-friendly options for everyday care. ${priceSummary}`,
      bullets: [
        `Browse ${lowerLabel} by concern, dosage form, and brand without jumping across multiple pages.`,
        "Compare listed prices and savings before opening a full product detail page.",
        featuredBrands ? `Featured brands in this collection include ${featuredBrands}.` : "Featured brands update with the active collection.",
        "Shortlists become easier when common options are shown together in one collection.",
        "Filters help narrow the view to familiar brands or more specific sub-categories.",
        "Related rails surface adjacent care options that shoppers often review together.",
        "A focused category page reduces friction for repeat buyers who already know what they need."
      ]
    },
    {
      heading: `How to Choose ${label}`,
      intro: "Start with the intended need, then compare pack details, pricing, and brand familiarity before adding an item to cart.",
      bullets: [
        "Use sub-categories first if you already know the product type or care goal.",
        "Check the product title and brand together to avoid selecting a similar-looking item by mistake.",
        "Review price and savings labels alongside pack size for a fair comparison.",
        "Open the product page for directions, warnings, and more detailed information when needed.",
        "If a medicine requires a prescription, keep your upload ready before checkout."
      ],
      outro: "This collection is designed to help users move from broad browsing into a confident product decision."
    },
    {
      heading: `Before You Buy ${label}`,
      intro: "A quick final review helps reduce ordering mistakes and makes repeat purchases easier later.",
      bullets: [
        "Confirm the dosage form, pack size, or strength shown in the product name.",
        "Review whether the item is suitable for daily use, short-term use, or specialist guidance.",
        "Use branded and generic comparisons where appropriate to check value.",
        "Look for savings badges, but prioritize suitability and instructions first.",
        "Move to checkout only after the item matches the intended care routine."
      ]
    }
  ];
}

function buildFaqs(title: string, products: CategoryPageProduct[], brandOptions: string[]) {
  const label = title.replace(/ Products$/, "").toLowerCase();
  const featuredBrand = brandOptions[0] ?? "the listed brands";
  const firstProduct = products[0]?.name ?? `the current ${label} collection`;

  return [
    {
      question: `How should I browse ${label} products?`,
      answer:
        "Start with the sub-category that best matches your need, then compare brand names, pack sizes, and prices before opening product details."
    },
    {
      question: "What is the best way to compare products on this page?",
      answer:
        `Use the listing to compare the product name, brand, savings, and listed price first, then open the detail page for directions, warnings, and pack information. ${firstProduct} is one of the products currently surfaced in this collection.`
    },
    {
      question: "Can I use this page to move between related collections?",
      answer:
        "Yes. The category and sub-category filters are meant to help you move across related collections without restarting your search."
    },
    {
      question: `What should I check before ordering ${label} items?`,
      answer:
        `Review the pack details, product type, and whether the item needs a prescription. For medicines, it is also useful to check directions and safety notes on the product page. If you already prefer ${featuredBrand}, use the brand filter to narrow the collection faster.`
    }
  ];
}

type ResolvedRoute = {
  navigation: NavCategory[];
  category: NavCategory;
  subcategory: NavSubcategory | null;
  itemLabel: string | null;
};

function resolveRoute(navigation: NavCategory[], slugs: string[]): ResolvedRoute | null {
  const category = navigation.find((entry) => entry.slug === slugs[0]);

  if (!category) {
    return null;
  }

  const subcategory = slugs[1]
    ? category.subcategories?.find((entry) => entry.slug === slugs[1]) ?? null
    : null;

  if (slugs[1] && !subcategory) {
    return null;
  }

  return {
    navigation,
    category,
    subcategory,
    itemLabel: slugs[2] ? formatTitle(slugs[2]) : null
  };
}

async function loadProductsForRoute(category: NavCategory, subcategory: NavSubcategory | null, itemSlug?: string) {
  const requestedSlugs = subcategory
    ? [subcategory.slug]
    : [category.slug, ...(category.subcategories?.map((entry) => entry.slug) ?? [])];

  const responses = await Promise.all(
    requestedSlugs.map(async (slug) => {
      try {
        return await fetchCatalogProducts({ category: slug });
      } catch {
        return [];
      }
    })
  );

  let products = uniqueProducts(responses.flat());

  if (itemSlug) {
    const filtered = products.filter((product) => matchesItemSlug(product, itemSlug));

    if (filtered.length > 0) {
      products = filtered;
    } else {
      products = [];
    }
  }

  return products;
}

export async function resolveCategoryPageLive(slugs: string[]): Promise<ResolvedCategoryPage | null> {
  try {
    const navigation = buildNavCatalog(await fetchCatalogCategories());
    const resolved = resolveRoute(navigation, slugs);

    if (!resolved) {
      return null;
    }

    const { category, subcategory, itemLabel } = resolved;
    const titleSource = itemLabel ?? subcategory?.label ?? category.label;
    const title = `${titleSource} Products`;
    const breadcrumbs: Array<{ label: string; href?: string }> = [
      { label: "Home", href: "/" },
      { label: "Categories", href: "/categories" },
      { label: category.label, href: category.href }
    ];

    if (subcategory) {
      breadcrumbs.push({ label: subcategory.label, href: subcategory.href });
    }

    if (itemLabel) {
      breadcrumbs.push({ label: itemLabel });
    }

    const liveProducts = mapApiProductsToCategoryProducts(await loadProductsForRoute(category, subcategory, slugs[2]));
    const brandOptions = Array.from(new Set(liveProducts.map((product) => product.brand))).sort((a, b) =>
      a.localeCompare(b)
    );

    return {
      breadcrumbs,
      title,
      categoryOptions: navigation.map((entry) => ({
        label: entry.label,
        href: entry.href,
        active: entry.slug === category.slug
      })),
      subcategoryOptions: (category.subcategories ?? []).map((entry) => ({
        label: entry.label,
        href: entry.href,
        active: entry.slug === subcategory?.slug
      })),
      brandOptions,
      products: liveProducts,
      content: buildContent(title, liveProducts, brandOptions),
      faqs: buildFaqs(title, liveProducts, brandOptions)
    };
  } catch {
    return null;
  }
}
