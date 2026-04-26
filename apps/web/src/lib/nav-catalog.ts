import type { ApiCatalogCategory } from "@/lib/api";

export type NavLeafItem = {
  id: number;
  slug: string;
  label: string;
  href: string;
  iconKey: string;
};

export type NavSubcategory = {
  id: number;
  slug: string;
  label: string;
  href: string;
  iconKey: string;
  items: NavLeafItem[];
};

export type NavCategory = {
  id: number;
  slug: string;
  label: string;
  href: string;
  iconKey: string;
  accent: string;
  soft: string;
  border: string;
  variant: "mega" | "simple";
  subcategories?: NavSubcategory[];
  items?: NavLeafItem[];
};

type CategoryTheme = {
  accent: string;
  soft: string;
  border: string;
};

const defaultTheme: CategoryTheme = {
  accent: "#1f6fe5",
  soft: "#edf5ff",
  border: "#c9ddff"
};

const categoryThemes: Array<{ matcher: RegExp; theme: CategoryTheme }> = [
  {
    matcher: /personal|skin|hair|baby|wellness|oral|elder/i,
    theme: { accent: "#ef7f4c", soft: "#fff3eb", border: "#ffd8c4" }
  },
  {
    matcher: /condition|heart|respirat|digest|kidney|liver|joint|pain|mental/i,
    theme: { accent: "#1ca486", soft: "#edfbf7", border: "#beece2" }
  },
  {
    matcher: /vitamin|supplement|protein|mineral|omega|immunity/i,
    theme: { accent: "#8b5cf6", soft: "#f4efff", border: "#dacfff" }
  },
  {
    matcher: /diabet|glucose|sugar/i,
    theme: { accent: "#0ea5e9", soft: "#eef9ff", border: "#c6ebff" }
  },
  {
    matcher: /device|monitor|nebul|brace|healthcare/i,
    theme: { accent: "#14b8a6", soft: "#effcfa", border: "#c2efe9" }
  },
  {
    matcher: /homeopath/i,
    theme: { accent: "#22c55e", soft: "#edfdf2", border: "#c7f0d4" }
  }
];

export function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function inferLeafIconKey(label: string, fallback = "sparkles") {
  const value = label.toLowerCase();

  if (value.includes("skin") || value.includes("acne") || value.includes("sunscreen") || value.includes("soap")) {
    return "sparkles";
  }
  if (value.includes("hair")) {
    return "hair";
  }
  if (
    value.includes("baby") ||
    value.includes("women") ||
    value.includes("ovulation") ||
    value.includes("sanitary")
  ) {
    return "baby";
  }
  if (
    value.includes("condom") ||
    value.includes("lubricant") ||
    value.includes("massage") ||
    value.includes("sexual")
  ) {
    return "heart";
  }
  if (
    value.includes("tooth") ||
    value.includes("mouth") ||
    value.includes("gargle") ||
    value.includes("ulcer")
  ) {
    return "smile";
  }
  if (
    value.includes("elder") ||
    value.includes("diaper") ||
    value.includes("mobility") ||
    value.includes("orthopaedic") ||
    value.includes("support")
  ) {
    return "shield";
  }
  if (value.includes("bone") || value.includes("joint") || value.includes("calcium") || value.includes("arthritis")) {
    return "bone";
  }
  if (
    value.includes("digest") ||
    value.includes("probiotic") ||
    value.includes("acidity") ||
    value.includes("gas") ||
    value.includes("constipation") ||
    value.includes("antacid")
  ) {
    return "stomach";
  }
  if (value.includes("eye") || value.includes("lens")) {
    return "eye";
  }
  if (value.includes("pain") || value.includes("spray") || value.includes("heating")) {
    return "flash";
  }
  if (value.includes("nicotine") || value.includes("smoking")) {
    return "nosmoke";
  }
  if (value.includes("liver") || value.includes("milk thistle")) {
    return "shield";
  }
  if (value.includes("cold") || value.includes("cough") || value.includes("nasal") || value.includes("lozenge")) {
    return "thermo";
  }
  if (value.includes("heart") || value.includes("bp") || value.includes("cholesterol")) {
    return "heart";
  }
  if (value.includes("kidney") || value.includes("uti") || value.includes("fluid")) {
    return "drop";
  }
  if (value.includes("respirat") || value.includes("asthma") || value.includes("breath") || value.includes("steam")) {
    return "lungs";
  }
  if (value.includes("stress") || value.includes("sleep") || value.includes("memory") || value.includes("focus")) {
    return "brain";
  }
  if (
    value.includes("vitamin") ||
    value.includes("multivitamin") ||
    value.includes("mineral") ||
    value.includes("omega") ||
    value.includes("immunity") ||
    value.includes("protein") ||
    value.includes("supplement")
  ) {
    return "capsule";
  }
  if (
    value.includes("glucose") ||
    value.includes("test strips") ||
    value.includes("lancet") ||
    value.includes("sugar") ||
    value.includes("diabet")
  ) {
    return "drop";
  }
  if (
    value.includes("monitor") ||
    value.includes("nebulizer") ||
    value.includes("vaporiz") ||
    value.includes("brace")
  ) {
    return "device";
  }
  if (value.includes("homeopathy")) {
    return "homeo";
  }
  if (
    value.includes("article") ||
    value.includes("story") ||
    value.includes("library") ||
    value.includes("guide") ||
    value.includes("diseases") ||
    value.includes("understanding")
  ) {
    return "guide";
  }
  if (
    value.includes("medicine") ||
    value.includes("generic") ||
    value.includes("chronic") ||
    value.includes("otc") ||
    value.includes("prescription")
  ) {
    return "medicine";
  }

  return fallback;
}

function resolveTheme(category: ApiCatalogCategory): CategoryTheme {
  const source = `${category.name} ${category.slug}`;
  return categoryThemes.find((entry) => entry.matcher.test(source))?.theme ?? defaultTheme;
}

function buildCategoryHref(category: ApiCatalogCategory) {
  return category.slug === "health-guide" ? "/health-guide" : `/categories/${category.slug}`;
}

function buildChildHref(parent: ApiCatalogCategory, child: ApiCatalogCategory) {
  if (parent.slug === "health-guide") {
    return `/health-guide/${child.slug}`;
  }

  return `/categories/${parent.slug}/${child.slug}`;
}

function buildLeafHref(parent: ApiCatalogCategory, child: ApiCatalogCategory, leaf: ApiCatalogCategory) {
  if (parent.slug === "health-guide") {
    return `/health-guide/${child.slug}/${leaf.slug}`;
  }

  return `/categories/${parent.slug}/${child.slug}/${leaf.slug}`;
}

export function buildNavCatalog(categories: ApiCatalogCategory[]): NavCategory[] {
  const childMap = new Map<number, ApiCatalogCategory[]>();
  const topLevel = categories.filter((category) => category.parent === null);

  for (const category of categories) {
    if (category.parent === null) {
      continue;
    }

    const siblings = childMap.get(category.parent) ?? [];
    siblings.push(category);
    childMap.set(category.parent, siblings);
  }

  return topLevel.map((category) => {
    const theme = resolveTheme(category);
    const children = (childMap.get(category.id) ?? []).map((subcategory) => ({
      id: subcategory.id,
      slug: subcategory.slug,
      label: subcategory.name,
      href: buildChildHref(category, subcategory),
      iconKey: inferLeafIconKey(subcategory.name, inferLeafIconKey(category.name)),
      items: (childMap.get(subcategory.id) ?? []).map((item) => ({
        id: item.id,
        slug: item.slug,
        label: item.name,
        href: buildLeafHref(category, subcategory, item),
        iconKey: inferLeafIconKey(item.name, inferLeafIconKey(subcategory.name))
      }))
    }));

    return {
      id: category.id,
      slug: category.slug,
      label: category.name,
      href: buildCategoryHref(category),
      iconKey: inferLeafIconKey(category.name, "sparkles"),
      accent: theme.accent,
      soft: theme.soft,
      border: theme.border,
      variant: children.length > 0 ? "mega" : "simple",
      subcategories: children,
      items: []
    };
  });
}
