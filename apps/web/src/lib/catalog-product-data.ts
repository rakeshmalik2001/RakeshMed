import { fetchCatalogProductBySlug, type ApiCatalogProductDetail, type ApiCatalogProductSummary } from "@/lib/api";
import { toProductSlug, type ResolvedCategoryPage } from "@/lib/category-page-data";
import { storefrontProducts, type StorefrontProduct } from "@/lib/storefront-data";

export type CatalogProductDetail = {
  slug: string;
  name: string;
  brand: string;
  manufacturer: string;
  off: string;
  mrp: string;
  price: string;
  pack: string;
  form: string;
  pricePerUnit: string;
  accent: string;
  breadcrumbs: Array<{ label: string; href?: string }>;
  composition: string;
  deliveryLabel: string;
  updatedOn?: string;
  quickLinks: Array<{ id: string; label: string }>;
  galleryItems: Array<{
    label: string;
    meta: string;
  }>;
  coupons: Array<{
    title: string;
    description: string;
    badge: string;
  }>;
  assuranceItems: Array<{
    label: string;
    iconKey: "check" | "alert" | "heart" | "image";
  }>;
  membership: {
    kicker: string;
    title: string;
    features: string[];
    ctaLabel: string;
  };
  highlights: string[];
  productHighlights: string[];
  description: string[];
  ingredients: string[];
  keyUses: string[];
  howToUse: string[];
  safetyInformation: string[];
  additionalInformation: Array<{
    label: string;
    bullets: string[];
  }>;
  faqs: Array<{
    question: string;
    answer: string;
  }>;
  warningCards: Array<{
    title: string;
    status: string;
    tone: "danger" | "info" | "warn";
    iconKey: "child" | "bottle" | "device" | "wash" | "droplet" | "alert" | "heart";
    body: string;
  }>;
  interactions: string[];
  usefulTests: string[];
  synopsis: Array<{
    label: string;
    value: string;
  }>;
  manufacturerDetails: {
    address: string;
    country: string;
    expiry: string;
    supportEmail: string;
    supportPhone: string;
  };
  certifiedContent: {
    writtenBy: string;
    writtenRole: string;
    reviewedBy: string;
    reviewedRole: string;
  };
  rails: {
    related: StorefrontProduct[];
    manufacturerMore: StorefrontProduct[];
    topSelling: StorefrontProduct[];
  };
  articleLinks: Array<{
    title: string;
    category: string;
  }>;
  textLinkSections: Array<{
    heading: string;
    text: string;
  }>;
  disclaimer?: string[];
};

const productDetailCache = new Map<string, CatalogProductDetail>();

const defaultManufacturerDetails: CatalogProductDetail["manufacturerDetails"] = {
  address: "Mumbai, Maharashtra",
  country: "India",
  expiry: "See package",
  supportEmail: "support@truecare.in",
  supportPhone: "9240250346"
};

const defaultCertifiedContent: CatalogProductDetail["certifiedContent"] = {
  writtenBy: "TrueCare Medical Content Team",
  writtenRole: "Medical Content",
  reviewedBy: "TrueCare Clinical Review Team",
  reviewedRole: "Clinical Review"
};

function slugLabel(value: string) {
  return value
    .replace(/-/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function splitTextBlock(value: string, fallback: string[] = []) {
  const entries = value
    .split(/\r?\n|[.;](?=\s|$)/)
    .map((entry) => entry.trim())
    .filter(Boolean)
    .slice(0, 8);

  return entries.length > 0 ? entries : fallback;
}

function formatMoney(value: string) {
  const amount = Number.parseFloat(value);
  if (Number.isNaN(amount)) {
    return value;
  }

  return Number.isInteger(amount) ? String(amount) : amount.toFixed(2);
}

function discountFromValues(mrp: string, salePrice: string) {
  const mrpValue = Number.parseFloat(mrp);
  const saleValue = Number.parseFloat(salePrice);

  if (Number.isNaN(mrpValue) || Number.isNaN(saleValue) || mrpValue <= 0 || saleValue >= mrpValue) {
    return "0% OFF";
  }

  return `${Math.round(((mrpValue - saleValue) / mrpValue) * 100)}% OFF`;
}

function railProductFromApi(product: ApiCatalogProductSummary): StorefrontProduct {
  return {
    slug: product.slug,
    name: product.name,
    off: discountFromValues(product.mrp, product.sale_price),
    mrp: formatMoney(product.mrp),
    price: formatMoney(product.sale_price),
    brand: product.brand?.name ?? product.manufacturer ?? "TrueCare",
    salt: product.composition || product.brand?.name || "General care composition",
    category: product.category.slug,
    form: product.dosage_form || "Product",
    useFor: product.category.name,
    tags: [product.stock_status.replace(/_/g, " "), product.requires_prescription ? "Rx" : "OTC"],
    meta: `${product.manufacturer || product.brand?.name || "TrueCare"} | ${product.pack_size || "Pack details"}`,
    rx: product.requires_prescription,
    pack: product.pack_size || "Pack of 1",
    uses: [product.category.name, product.composition || "Compare product details before purchase"]
  };
}

function titleFromSlug(value: string) {
  return value
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function toCategorySlugs(href: string) {
  return href
    .replace(/^\/categories\//, "")
    .split("/")
    .filter(Boolean);
}

function manufacturerForBrand(brand: string) {
  const known: Record<string, string> = {
    Skinshine: "Cadila Pharmaceuticals Ltd",
    Soft: "Leeford Healthcare",
    Alite: "Alite Healthcare",
    Moiz: "Glowderma",
    Brinton: "Brinton Pharmaceuticals",
    Sunban: "Sun Pharmaceutical Industries Ltd",
    Golite: "USV Pvt Ltd",
    Ahaglow: "Torrent Pharmaceuticals Ltd",
    Excela: "Cipla Health",
    Photostable: "Sun Pharma",
    Episoft: "Glenmark",
    "Acne UV": "Ipca Laboratories",
    Cetaphil: "Galderma India Pvt Ltd",
    Venusia: "Dr. Reddy's Laboratories Ltd"
  };

  return known[brand] ?? `${brand} Healthcare Pvt Ltd`;
}

function getContextualArticleLinks(label: string) {
  const value = label.toLowerCase();

  if (value.includes("diabet")) {
    return [
      { title: "How to choose diabetes care products for daily monitoring", category: "Diabetes Care" },
      { title: "What to check before reordering glucose test strips", category: "Diabetes Care" },
      { title: "When home sugar tracking helps and when to speak with a doctor", category: "Health Guide" }
    ];
  }

  if (value.includes("heart") || value.includes("cholesterol")) {
    return [
      { title: "How to compare cholesterol medicines by salt and strength", category: "Heart Care" },
      { title: "What matters most in a repeat cardiac medicine refill", category: "Heart Care" },
      { title: "A quick guide to prescription refills and medicine adherence", category: "Health Guide" }
    ];
  }

  if (value.includes("device") || value.includes("monitor") || value.includes("respirat")) {
    return [
      { title: "Choosing the right home healthcare device for regular use", category: "Healthcare Devices" },
      { title: "How to compare monitors, nebulizers, and support devices online", category: "Healthcare Devices" },
      { title: "What to check before buying a home-use medical device", category: "Health Guide" }
    ];
  }

  if (value.includes("vitamin") || value.includes("supplement")) {
    return [
      { title: "How to compare wellness supplements by format and daily use", category: "Vitamins & Supplements" },
      { title: "What to know before adding a vitamin routine to your cart", category: "Vitamins & Supplements" },
      { title: "When nutrition support is routine and when expert advice helps", category: "Health Guide" }
    ];
  }

  return [
    { title: "How to compare generic medicines without guesswork", category: "Medicine Savings" },
    { title: "What to keep ready before uploading a prescription", category: "Order Prep" },
    { title: "When a refill is routine and when to recheck with a doctor", category: "Care Guidance" }
  ];
}

function getContextualTextLinkSections(label: string) {
  const value = label.toLowerCase();

  if (value.includes("diabet")) {
    return [
      {
        heading: "Top-Searched Diabetes Care",
        text: "Accu-Chek Active Test Strips | Contour Plus Test Strips | Sugar monitoring supplies | Glucose care essentials | View More"
      },
      {
        heading: "Monitoring Support",
        text: "Compare strips, lancets, and device compatibility before you reorder routine diabetes care products."
      },
      {
        heading: "Related Products",
        text: "Find nearby options in diabetes support, nutrition products, and home-use monitoring categories."
      }
    ];
  }

  if (value.includes("device") || value.includes("monitor") || value.includes("respirat")) {
    return [
      {
        heading: "Top-Searched Healthcare Devices",
        text: "Blood pressure monitors | Nebulizers | Thermometers | Glucometers | Home-use support devices | View More"
      },
      {
        heading: "Device Buying Tips",
        text: "Compare purpose, ease of use, and routine care needs before choosing a home-use healthcare device."
      },
      {
        heading: "Related Products",
        text: "Explore adjacent device categories and supporting daily care items often reviewed together."
      }
    ];
  }

  return [
    {
      heading: "Top-Searched Medicines",
      text: "Telma 40 | Ecosprin 75 | Atorva 10 | Rosuvas 10 | Limcee | Electral | View More"
    },
    {
      heading: "Popular Care Categories",
      text: "Heart care | Vitamins and supplements | Diabetes care | Healthcare devices | Prescription support"
    },
    {
      heading: "Related Products",
      text: "Find nearby alternatives, same-category products, and related care options in one place."
    }
  ];
}

function buildWarningCards(values: string[], productName: string) {
  const warningTemplates = [
    { title: "Pregnancy", status: "Contraindicated", tone: "danger", iconKey: "child" },
    { title: "Breastfeeding", status: "Consult your doctor", tone: "info", iconKey: "bottle" },
    { title: "Driving and Using Machines", status: "Use with caution", tone: "warn", iconKey: "device" },
    { title: "Alcohol", status: "Consult your doctor", tone: "info", iconKey: "wash" },
    { title: "Kidney", status: "Use with caution", tone: "warn", iconKey: "droplet" },
    { title: "Allergy", status: "Contraindicated", tone: "danger", iconKey: "alert" },
    { title: "Heart Disease", status: "Use with caution", tone: "warn", iconKey: "heart" },
    { title: "Use In Pediatrics", status: "Contraindicated", tone: "danger", iconKey: "child" },
    { title: "Use In Geriatrics", status: "Use with caution", tone: "warn", iconKey: "child" }
  ] as const;

  return warningTemplates.map((template, index) => ({
    ...template,
    body:
      values[index] ??
      `${productName.toUpperCase()} should be reviewed carefully in relation to ${template.title.toLowerCase()}. Consult your doctor before taking it.`
  }));
}

function buildUsefulTests(name: string, composition: string, keyUses: string[]) {
  const lower = `${name} ${composition} ${keyUses.join(" ")}`.toLowerCase();

  if (lower.includes("diabet")) {
    return [
      "HbA1c (glycated haemoglobin)",
      "Blood glucose fasting (FBS)",
      "Random blood sugar (RBS)",
      "Post-prandial blood sugar (PPBS)"
    ];
  }

  if (lower.includes("sun") || lower.includes("skin")) {
    return [
      "Dermatology consultation",
      "Skin sensitivity review",
      "Patch test evaluation"
    ];
  }

  return [
    "Review product label instructions",
    "Check pack details before use",
    "Consult a doctor or pharmacist when unsure"
  ];
}

function buildInteractions(additionalInformation: CatalogProductDetail["additionalInformation"]) {
  const bullets = additionalInformation.flatMap((group) => group.bullets).slice(0, 5);

  if (bullets.length > 0) {
    return bullets;
  }

  return ["Consult your doctor before combining this product with any other treatment or daily care routine."];
}

function buildGalleryItems(name: string, brand: string, pack: string) {
  return [
    { label: "Front", meta: name },
    { label: "Back", meta: brand },
    { label: "Label", meta: pack }
  ];
}

function buildCoupons(price: string) {
  return [
    {
      title: `Best price Rs.${price}`,
      description: "Add medicines worth Rs.999 more to your cart",
      badge: "Unlock coupon"
    },
    {
      title: "Get extra 5% OFF + 2% cashback",
      description: "Minimum cart value: Rs.500",
      badge: "EXTRA"
    }
  ];
}

function buildAssuranceItems() {
  return [
    { label: "Fresh expiry assurance", iconKey: "check" },
    { label: "Return support available", iconKey: "alert" },
    { label: "Authentic product sourcing", iconKey: "heart" },
    { label: "Quality reviewed packs", iconKey: "image" }
  ] as const;
}

function buildMembership() {
  return {
    kicker: "TrueCare Plus Membership",
    title: "Starting at just Rs.19 for 3 months.",
    features: [
      "Unlimited FREE delivery above 799",
      "2% cashback on medicines",
      "Extra 10% off on lab test"
    ],
    ctaLabel: "View Plans"
  };
}

function emptyRails(): CatalogProductDetail["rails"] {
  return {
    related: [],
    manufacturerMore: [],
    topSelling: []
  };
}

function buildSynopsis(values: { composition: string; brand: string; keyUses: string[]; form: string }) {
  return [
    { label: "Drug", value: values.composition },
    { label: "Brand", value: values.brand },
    { label: "Therapeutic indication", value: values.keyUses[0] ?? "See product information" },
    { label: "Dosage form", value: values.form }
  ];
}

function railProductFromValues(values: {
  slug: string;
  name: string;
  brand: string;
  off: string;
  mrp: string;
  price: string;
  useFor: string;
  pack: string;
  form: string;
}) {
  return {
    slug: values.slug,
    name: values.name,
    off: values.off,
    mrp: values.mrp,
    price: values.price,
    brand: values.brand,
    salt: values.brand,
    category: values.useFor.toLowerCase().replace(/\s+/g, "-"),
    form: values.form,
    useFor: values.useFor,
    tags: ["In stock", "Best savings"],
    meta: `${values.brand} | ${values.pack}`,
    rx: false,
    pack: values.pack,
    uses: [`Supports ${values.useFor.toLowerCase()} goals`, "Useful for daily care routines"]
  } satisfies StorefrontProduct;
}

function buildDetailFromCollectionPage(
  page: ResolvedCategoryPage,
  product: ResolvedCategoryPage["products"][number]
) {
  const activeLeaf = page.breadcrumbs.at(-1)?.label !== page.title.replace(/ Products$/, "")
    ? page.breadcrumbs.at(-1)?.label
    : undefined;
  const groupLabel = activeLeaf ?? page.title.replace(/ Products$/, "");
  const manufacturer = manufacturerForBrand(product.brand);
  const pack = product.name.match(/(\d+\s?(ml|gm|gms|tablet|tablets|capsule|capsules))/i)?.[0] ?? "Tube of 100 ML";
  const form = /gel/i.test(product.name)
    ? "Gel"
    : /cleanser|face wash|wash/i.test(product.name)
      ? "Cleanser"
      : /lotion/i.test(product.name)
        ? "Lotion"
        : "Cream";
  const priceValue = Number(product.price);
  const unit = pack.toLowerCase().includes("ml") ? "ML" : "GM";
  const unitCountMatch = pack.match(/(\d+)/);
  const unitCount = unitCountMatch ? Number(unitCountMatch[1]) : 100;
  const perUnit = unitCount > 0 ? (priceValue / unitCount).toFixed(2) : product.price;
  const supportCategory = page.breadcrumbs[2]?.label ?? "Categories";
  const subCategory = page.breadcrumbs[3]?.label;

  const related = page.products
    .filter((entry) => entry.slug !== product.slug)
    .slice(0, 8)
    .map((entry) =>
      railProductFromValues({
        slug: entry.slug,
        name: entry.name,
        brand: entry.brand,
        off: entry.off,
        mrp: entry.mrp,
        price: entry.price,
        useFor: subCategory ?? supportCategory,
        pack,
        form
      })
    );

  const manufacturerMore = page.products
    .filter((entry) => entry.brand === product.brand && entry.slug !== product.slug)
    .slice(0, 8)
    .map((entry) =>
      railProductFromValues({
        slug: entry.slug,
        name: entry.name,
        brand: entry.brand,
        off: entry.off,
        mrp: entry.mrp,
        price: entry.price,
        useFor: subCategory ?? supportCategory,
        pack,
        form
      })
    );

  const topSelling = page.products
    .slice()
    .reverse()
    .filter((entry) => entry.slug !== product.slug)
    .slice(0, 8)
    .map((entry) =>
      railProductFromValues({
        slug: entry.slug,
        name: entry.name,
        brand: entry.brand,
        off: entry.off,
        mrp: entry.mrp,
        price: entry.price,
        useFor: supportCategory,
        pack,
        form
      })
    );

  const detail = {
    slug: product.slug,
    name: product.name,
    brand: product.brand,
    manufacturer,
    off: product.off,
    mrp: product.mrp,
    price: product.price,
    pack: `Tube of ${pack.toUpperCase()}`,
    form,
    pricePerUnit: `${perUnit}/${unit}`,
    accent: product.accent,
    breadcrumbs: [
      ...page.breadcrumbs.slice(0, -1),
      { label: product.name }
    ],
    composition: `${product.brand} care blend (0 Mg)`,
    deliveryLabel: "Tomorrow 10 PM",
    updatedOn: "09 Sep. 2025 | 4:59PM (IST)",
    quickLinks: [
      { id: "uses", label: "Uses" },
      { id: "how-it-works", label: "How it works" },
      { id: "how-to-use", label: "Directions for use" },
      { id: "side-effects", label: "Side effects" },
      { id: "warning-precautions", label: "Warning & precautions" },
      { id: "interactions", label: "Interactions" },
      { id: "synopsis", label: "Synopsis" },
      { id: "useful-tests", label: "Useful diagnostic tests" },
      { id: "faq", label: "FAQs" },
      { id: "learn-more", label: "Learn more" }
    ],
    galleryItems: buildGalleryItems(product.name, product.brand, `Tube of ${pack.toUpperCase()}`),
    coupons: buildCoupons(product.price),
    assuranceItems: [...buildAssuranceItems()],
    membership: buildMembership(),
    highlights: [
      `${groupLabel} focused formula designed for regular use.`,
      `Supports daily ${groupLabel.toLowerCase()} care routines with lightweight application.`,
      "Created for easy comparison inside the collection and product experience.",
      "Suitable for users browsing discounted care essentials online."
    ],
    productHighlights: [
      `${groupLabel} focused formula designed for regular use.`,
      `Supports daily ${groupLabel.toLowerCase()} care routines with lightweight application.`,
      "Comfortable texture intended for easy everyday application.",
      "Useful for shoppers comparing discounted skincare products online."
    ],
    description: [
      `${product.name} is presented in this Truemeds-style product page so customers can move from collection browsing into a more detailed product view with pricing, delivery, and informational content in one place.`,
      `This product sits under ${supportCategory}${subCategory ? ` / ${subCategory}` : ""} and is designed to support customers comparing ${groupLabel.toLowerCase()} options before adding them to cart.`,
      `The lightweight structure, clear pricing, and quick links mirror the medicine-style detail flow shown in the reference screens.`
    ],
    ingredients: [
      `${product.brand} base complex helps support routine ${groupLabel.toLowerCase()} care.`,
      "Humectant and emollient support may help maintain hydration and smooth spreadability.",
      "Lightweight stabilisers help the formula absorb comfortably during routine use.",
      "Protective care ingredients may help support a soft finish and comfortable wear."
    ],
    keyUses: [
      `Helps support ${groupLabel.toLowerCase()} care goals during regular use.`,
      "Useful when comparing branded care products by price and savings.",
      "May support a smoother, more comfortable daily routine.",
      "Built to make browsing, evaluating, and selecting care products simpler."
    ],
    howToUse: [
      "Apply on clean, dry skin or the intended area as needed.",
      "Spread evenly using a small amount and allow it to absorb fully.",
      "Reapply according to routine needs or packaging guidance.",
      "Use consistently for a smoother care routine."
    ],
    safetyInformation: [
      "For external use only.",
      "Avoid direct contact with eyes and rinse thoroughly if contact occurs.",
      "Patch test before first use if you have sensitive skin.",
      "Store below 30C in a cool and dry place."
    ],
    additionalInformation: [
      {
        label: "Good to Know",
        bullets: [
          `Brand: ${product.brand}`,
          `Category: ${supportCategory}`,
          subCategory ? `Sub-category: ${subCategory}` : "Sub-category: General selection",
          `Pack size: ${pack}`,
          "Pricing and savings are shown directly on the page for faster comparison."
        ]
      },
      {
        label: "Quick Tips",
        bullets: [
          "Use the quick links panel to jump to the section you need most.",
          "Compare related products lower on the page before checkout.",
          "Review manufacturer details and FAQs if you want more confidence before buying."
        ]
      }
    ],
    faqs: [
      {
        question: `What is ${product.name} used for?`,
        answer: `${product.name} is positioned as a ${groupLabel.toLowerCase()} product that supports routine care, product comparison, and quick purchase decisions.`
      },
      {
        question: "Can I compare this with other options from the same category?",
        answer: "Yes. The page includes related and top-selling product rails so users can compare nearby alternatives without leaving the detail flow."
      },
      {
        question: "Is this page available for other catalog products too?",
        answer: "Yes. The same reusable product detail logic has been connected across category and sub-category product cards."
      },
      {
        question: "Where can I find more details about the product?",
        answer: "Use the quick links panel to jump to the description, ingredients, key uses, safety information, and FAQs sections."
      }
    ],
    warningCards: buildWarningCards(
      [
        "Consult your doctor before use during pregnancy.",
        "If breastfeeding, use only after professional guidance.",
        "Review routine use carefully if you need full alertness for daily tasks.",
        "Avoid combining use with alcohol unless a clinician says it is appropriate.",
        "Use carefully if you have kidney-related health concerns.",
        "Do not continue use if you notice signs of sensitivity or allergy.",
        "Review existing heart conditions before adding this product to your routine."
      ],
      product.name
    ),
    interactions: [
      "Review the label and routine use guidance before combining with other treatments.",
      "Compare similar products carefully if you are switching from another formulation.",
      "Ask a doctor or pharmacist if you are unsure how this fits into your current care routine."
    ],
    usefulTests: buildUsefulTests(product.name, `${product.brand} care blend (0 Mg)`, [
      `Helps support ${groupLabel.toLowerCase()} care goals during regular use.`
    ]),
    synopsis: buildSynopsis({
      composition: `${product.brand} care blend (0 Mg)`,
      brand: product.brand,
      keyUses: [
        `Helps support ${groupLabel.toLowerCase()} care goals during regular use.`,
        "Useful when comparing branded care products by price and savings."
      ],
      form
    }),
    manufacturerDetails: {
      address: "5V74+4P2, Jay Prakash Nagar, Goregaon, Mumbai, Maharashtra 400063",
      country: "India",
      expiry: "August 2026",
      supportEmail: "support@truemeds.in",
      supportPhone: "9240250346"
    },
    certifiedContent: {
      writtenBy: "Dr. Nikhil Sharma",
      writtenRole: "Medical Content Writer | 5 years M.S Orthopaedics",
      reviewedBy: "Dr. Mandeep Chadha",
      reviewedRole: "Lead Medical Content Reviewer | 12 years MBBS, DNB (OBGY)"
    },
    rails: {
      related,
      manufacturerMore: manufacturerMore.length > 0 ? manufacturerMore : related.slice(0, 6),
      topSelling: topSelling.length > 0 ? topSelling : related.slice(0, 6)
    },
    articleLinks: getContextualArticleLinks(groupLabel),
    textLinkSections: getContextualTextLinkSections(groupLabel),
    disclaimer: [
      "We, at Truemeds make a diligent attempt to deliver accurate, expert-drafted and thoroughly reviewed medicine related information to our consumers.",
      "However, it should by no means be considered a substitute for prescription from a certified doctor or a trustworthy doctor-patient relationship.",
      "The sole purpose of the information on this portal is to educate consumers, which helps support a better understanding of health products before purchase."
    ]
  } satisfies CatalogProductDetail;

  if (product.slug === toProductSlug("Skinshine SPF 30 Sunscreen Lotion 100ml")) {
    detail.composition = "All Other Combinations (0 Mg)";
    detail.highlights = [
      "Broad-spectrum SPF 30 sunscreen protects against UVA/UVB rays.",
      "Enriched with nanoparticles and liquorice extract for enhanced skincare.",
      "Manages sunburn and premature skin ageing.",
      "Hydrates, smoothens, and softens skin while protecting.",
      "Provides a matte finish without leaving a white cast.",
      "Lightweight, non-greasy formula suitable for all skin types."
    ];
    detail.productHighlights = detail.highlights;
    detail.description = [
      "Skinshine SPF 30 Sunscreen Lotion 100ml is used for protecting the skin from harmful sun exposure while maintaining hydration and nourishment.",
      "Formulated with nanoparticles and liquorice extracts, it supports broad-spectrum UVA/UVB protection, helping manage sunburn, pigmentation, and premature ageing.",
      "The sunscreen forms a protective barrier, shielding the skin from UV rays that may contribute to sun damage, fine lines, and uneven skin tone.",
      "Liquorice extract in the formula helps manage hyperpigmentation and soothes the skin, making it suitable for all skin types.",
      "With its lightweight, non-greasy consistency, the lotion spreads easily and absorbs quickly without clogging pores. It provides a smooth, mattified finish, helping in daily sun protection.",
      "The formula hydrates and softens the skin while protecting it from environmental stressors. Designed for all skin types, including sensitive skin, Skinshine SPF 30 Sunscreen Lotion ensures effective sun defence and can be reapplied to maintain continuous protection."
    ];
    detail.ingredients = [
      "Liquorice Extract: Helps manage uneven skin tone and pigmentation by reducing melanin production. It contains glabridin, which has soothing and antioxidant properties that may help address sun-induced skin damage while supporting skin brightness and hydration.",
      "Avobenzone: A broad-spectrum UV filter that helps manage sun-induced skin damage by absorbing harmful UVA rays and reducing oxidative stress caused by prolonged sun exposure.",
      "Ethylhexyl Methoxy Cinnamate (Octinoxate): Helps manage UVB ray absorption, reducing the risk of sunburn and supporting protection from environmental aggression.",
      "Titanium Dioxide: A mineral-based UV blocker that helps manage sun damage by reflecting and scattering harmful rays. It is photostable and may help manage skin sensitivity caused by UV exposure.",
      "Glycerin: A natural humectant that attracts moisture to help maintain skin hydration. It also supports skin elasticity and reduces dryness caused by sun exposure.",
      "Other Ingredients: Allantoin, Benzophenone-3, Carbopol 940, Cetyl Alcohol, Ceto Stearyl Alcohol, Cyclopentasiloxane, Dimethicone, Emulsifying Wax, Isopropyl Myristate, Light Liquid Paraffin, Sodium PCA, Octocrylene, Polyacrylate, Sorbitol, Stearic Acid, Stearyl Alcohol, Triethanolamine, Vitamin E Acetate, Colour, Perfume, Aqua, Sodium Benzoate, Methyl Paraben, Propyl Paraben."
    ];
    detail.keyUses = [
      "Help Protect Against Sunburn: Skinshine SPF 30 Sunscreen Lotion might help shield the skin from harmful UVB rays that contribute to sunburn. Regular use may also assist in managing skin irritation, redness, and peeling caused by excessive sun exposure.",
      "Help Manage Premature Aging: Prolonged sun exposure may accelerate the appearance of fine lines and wrinkles. This sunscreen might help maintain skin elasticity and hydration, supporting youthful, healthy-looking skin.",
      "Help Reduce Hyperpigmentation: Liquorice extract in the formula might help manage dark spots, uneven skin tone, and sunspots caused by excessive sun exposure. It may also support skin brightness and radiance.",
      "Help Maintain Skin Hydration: This sunscreen, enriched with moisturising agents like glycerin and light liquid paraffin, may help keep the skin hydrated and manage dryness and roughness that could result from sun exposure.",
      "Provide Broad-Spectrum Protection: This sunscreen might help manage UVA/UVB damage by forming a protective barrier on the skin, reducing the effects of sun-induced stress.",
      "Help in Achieving a Matte Finish: The non-greasy and lightweight formula might absorb excess oil while leaving the skin with a smooth, matte finish, making it suitable for everyday wear."
    ];
    detail.howToUse = [
      "Apply liberally 20 minutes before sun exposure.",
      "Spread evenly on the face, neck, arms, and other exposed areas.",
      "Reapply if required, especially after sweating or swimming."
    ];
    detail.safetyInformation = [
      "For external use only.",
      "Avoid direct contact with eyes. In case of contact, rinse with water immediately.",
      "Store below 30°C in a dry and dark place.",
      "Use 24 months before the manufacturing date."
    ];
    detail.additionalInformation = [
      {
        label: "Good to Know",
        bullets: [
          "SPF: 30.",
          "Suitable For: All Skin Types.",
          "Ideal For: Both Men and Women.",
          "Natural Formula.",
          "Enriched with nanoparticles for better absorption.",
          "Non-comedogenic.",
          "Dermatologically tested."
        ]
      },
      {
        label: "Quick Tips",
        bullets: [
          "Apply sunscreen even on cloudy days to ensure continuous UV protection.",
          "Use under makeup for added sun protection."
        ]
      },
      {
        label: "Concerns It Can Help With",
        bullets: ["Sunburn", "Tanning", "Premature aging", "Dryness", "Pigmentation"]
      },
      {
        label: "Area of Application",
        bullets: ["Face, neck, arms, legs, and other exposed skin areas."]
      }
    ];
    detail.faqs = [
      {
        question: "Can I use this sunscreen under makeup?",
        answer: "Skinshine SPF 30 Sunscreen Lotion has a lightweight, non-greasy formula that allows easy layering under makeup."
      },
      {
        question: "How often should I reapply this sunscreen?",
        answer: "Reapply every 2 to 3 hours during prolonged sun exposure and sooner after sweating or swimming."
      },
      {
        question: "Is this sunscreen suitable for oily skin?",
        answer: "Yes, the formula is lightweight and designed to leave a smoother matte finish, which can feel more comfortable for oily or combination skin."
      },
      {
        question: "Does it leave a white cast on the skin?",
        answer: "The lotion is designed to provide sun protection with a more blendable finish and may help minimise a visible white cast when applied evenly."
      },
      {
        question: "Can this sunscreen be used on sensitive skin?",
        answer: "It is designed for all skin types, including sensitive skin, but a patch test is still a good idea before first use."
      },
      {
        question: "Is this sunscreen waterproof?",
        answer: "It can provide routine daily protection, but reapplication is recommended after sweating, washing, or swimming."
      }
    ];
    detail.manufacturerDetails = {
      address: "5V74+4P2, Jay Prakash Nagar, Goregaon, Mumbai, Maharashtra 400063",
      country: "INDIA",
      expiry: "August 2026",
      supportEmail: "support@truemeds.in",
      supportPhone: "9240250346"
    };
    detail.textLinkSections = [
      {
        heading: "Top-Searched Medicines",
        text: "Telma 40 | Udiliv 300 | Cogniza | Cheston Cold | Skinshine Cream | Ecosprin 75 | Amoxyclav 625 | Rt O Capsule | Hmet Tablet | Ketokol Shampoo | Montewok Lc | Nflox Tz | Klmline Lotion | Clagen | Cypin Syrup | Neurovein Lc | Kozicare Cream | Cefix 200 | Deriphyllin | View More"
      },
      {
        heading: "Top-Selling Healthcare Devices",
        text: "Dr Morepen Mt 110 Digi Classic Digital Thermometer | Rotahaler Device | Lupihaler Device | Dr Morepen Bp 14 Blood Pressure Monitor | Omron Hem 7124 Automatic Blood Pressure Monitor | Dr Morepen Bg 03 Gluco One Blood Glucose Monitoring System | OneTouch Select Plus Simple Glucometer | Omron Hem 7156 Automatic Blood Pressure Monitor | View More"
      },
      {
        heading: "Related Products",
        text: "Actipro Powder 100 Gm | Ahaglow Advanced Face Wash Gel 100gm | Ahaglow S Foaming Face Wash 60ml | Aimil Amyron Tablet 30 | Aquasoft S Syndet Bar 75gm | C.V.P. Forte 300 Mg Capsule 10 | Caladoux Calamine Soothing Lotion 50ml | Calapure A Lotion 100ml | Dandle Plus Anti Dandruff Shampoo 100gm | Dermoys 365 Lotion | View More"
      }
    ];
    detail.disclaimer = [
      "We, at Truemeds make a diligent attempt to deliver accurate, expert-drafted and thoroughly reviewed medicine related information to our consumers.",
      "However, it should by no means be considered a substitute for prescription from a certified doctor or a trustworthy doctor-patient relationship.",
      "In fact we detest any form of self medication without expert advice. The sole purpose of the information on our portals is to educate our consumers which helps improve doctor-patient relationships."
    ];
  }

  detail.galleryItems = buildGalleryItems(detail.name, detail.brand, detail.pack);
  detail.coupons = buildCoupons(detail.price);
  detail.assuranceItems = [...buildAssuranceItems()];
  detail.membership = buildMembership();
  detail.warningCards = buildWarningCards(detail.safetyInformation, detail.name);
  detail.interactions = buildInteractions(detail.additionalInformation);
  detail.usefulTests = buildUsefulTests(detail.name, detail.composition, detail.keyUses);
  detail.synopsis = buildSynopsis({
    composition: detail.composition,
    brand: detail.brand,
    keyUses: detail.keyUses,
    form: detail.form
  });

  return detail;
}

function seedStorefrontProducts() {
  for (const product of storefrontProducts) {
    if (productDetailCache.has(product.slug)) {
      continue;
    }

    const manufacturer = manufacturerForBrand(product.brand);
    const relatedPool = storefrontProducts.filter((entry) => entry.slug !== product.slug);

    productDetailCache.set(product.slug, {
      slug: product.slug,
      name: product.name,
      brand: product.brand,
      manufacturer,
      off: product.off,
      mrp: product.mrp,
      price: product.price,
      pack: product.pack,
      form: product.form,
      pricePerUnit: `${product.price}/${product.form.toUpperCase()}`,
      accent: "#eff8ff",
      breadcrumbs: [
        { label: "Home", href: "/" },
        { label: "Medicines", href: "/categories" },
        { label: titleFromSlug(product.category), href: "/categories" },
        { label: product.name }
      ],
      composition: `${product.salt} (0 Mg)`,
      deliveryLabel: "Tomorrow 10 PM",
      quickLinks: [
        { id: "uses", label: "Uses" },
        { id: "how-it-works", label: "How it works" },
        { id: "how-to-use", label: "Directions for use" },
        { id: "side-effects", label: "Side effects" },
        { id: "warning-precautions", label: "Warning & precautions" },
        { id: "interactions", label: "Interactions" },
        { id: "synopsis", label: "Synopsis" },
        { id: "useful-tests", label: "Useful diagnostic tests" },
        { id: "faq", label: "FAQs" },
        { id: "learn-more", label: "Learn more" }
      ],
      galleryItems: buildGalleryItems(product.name, product.brand, product.pack),
      coupons: buildCoupons(product.price),
      assuranceItems: [...buildAssuranceItems()],
      membership: buildMembership(),
      highlights: product.uses,
      productHighlights: product.uses,
      description: [
        `${product.name} is a medicine-style product detail page with richer information, pricing, and supporting sections for easier comparison.`,
        `${product.name} from ${product.brand} is shown with pack size, composition, and related alternatives to match the Truemeds reference layout.`
      ],
      ingredients: [`Active ingredient: ${product.salt}`, `${product.brand} branded formulation`, "Supportive inactive ingredients vary by pack."],
      keyUses: product.uses,
      howToUse: [
        "Use as directed on the label or by your doctor.",
        "Follow the recommended timing and dosage instructions.",
        "Do not exceed the recommended amount unless advised."
      ],
      safetyInformation: [
        "Read the label carefully before use.",
        product.rx ? "Use only under medical supervision." : "Use responsibly according to package instructions.",
        "Store in a cool and dry place away from direct sunlight."
      ],
      additionalInformation: [
        {
          label: "Good to Know",
          bullets: [`Pack: ${product.pack}`, `Brand: ${product.brand}`, `Use for: ${product.useFor}`]
        }
      ],
      faqs: [
        {
          question: `What is ${product.name} used for?`,
          answer: `${product.name} is commonly chosen for ${product.useFor.toLowerCase()} support and is shown with related options for easier comparison.`
        },
        {
          question: "Can I compare substitutes or related products?",
          answer: "Yes. The page includes related product rails to help compare nearby alternatives."
        }
      ],
      warningCards: buildWarningCards(
        [
          "Read the label carefully before use.",
          product.rx ? "Use only under medical supervision." : "Use responsibly according to package instructions.",
          "Store in a cool and dry place away from direct sunlight."
        ],
        product.name
      ),
      interactions: buildInteractions([
        {
          label: "Good to Know",
          bullets: [`Pack: ${product.pack}`, `Brand: ${product.brand}`, `Use for: ${product.useFor}`]
        }
      ]),
      usefulTests: buildUsefulTests(product.name, `${product.salt} (0 Mg)`, product.uses),
      synopsis: buildSynopsis({
        composition: `${product.salt} (0 Mg)`,
        brand: product.brand,
        keyUses: product.uses,
        form: product.form
      }),
      manufacturerDetails: {
        address: "6th floor, Urmi Corporate Park Solaris, Saki Vihar Road, Andheri East, Mumbai 400072",
        country: "India",
        expiry: "August 2026",
        supportEmail: "support@truemeds.in",
        supportPhone: "9240250346"
      },
      certifiedContent: {
        writtenBy: "Dr. Nikhil Sharma",
        writtenRole: "Medical Content Writer | 5 years M.S Orthopaedics",
        reviewedBy: "Dr. Mandeep Chadha",
        reviewedRole: "Lead Medical Content Reviewer | 12 years MBBS, DNB (OBGY)"
      },
      rails: {
        related: relatedPool.slice(0, 8),
        manufacturerMore: relatedPool.filter((entry) => entry.brand === product.brand).slice(0, 8),
        topSelling: relatedPool.slice(0, 8)
      },
      articleLinks: getContextualArticleLinks("General Medicines"),
      textLinkSections: getContextualTextLinkSections("General Medicines"),
      disclaimer: [
        "This page is intended to support product understanding and should not replace professional medical advice.",
        "Always read the label and use the product according to packaging guidance or doctor recommendation."
      ]
    });
  }
}

seedStorefrontProducts();

export function getCatalogProductBySlug(slug: string) {
  return productDetailCache.get(slug) ?? null;
}

export async function getLiveCatalogProductBySlug(slug: string) {
  try {
    const product = await fetchCatalogProductBySlug(slug);

    if (!product) {
      return getCatalogProductBySlug(slug);
    }

    const fallback = getCatalogProductBySlug(slug);
    const related = product.substitutes.map(railProductFromApi);
      const manufacturerMore = fallback?.rails.manufacturerMore.filter((entry) => entry.slug !== slug) ?? [];
      const topSelling = fallback?.rails.topSelling.filter((entry) => entry.slug !== slug) ?? [];
    const brandName = product.brand?.name ?? product.manufacturer ?? "TrueCare";
    const warnings = splitTextBlock(product.warnings, [
      "Consult your doctor before using this product if you have an ongoing condition or prescription."
    ]);
    const sideEffects = splitTextBlock(product.side_effects, [
      "Read the label carefully and seek professional guidance if anything feels unusual after use."
    ]);
    const description = splitTextBlock(product.description, [
      `${product.name} is part of the live catalog and is shown with pricing, pack details, and supporting information for easier decision-making.`
    ]);
    const storageInformation = splitTextBlock(product.storage_instructions, [
      "Store in a cool and dry place away from direct sunlight."
    ]);

    return {
      slug: product.slug,
      name: product.name,
      brand: brandName,
      manufacturer: product.manufacturer || brandName,
      off: discountFromValues(product.mrp, product.sale_price),
      mrp: formatMoney(product.mrp),
      price: formatMoney(product.sale_price),
      pack: product.pack_size || fallback?.pack || "Pack of 1",
      form: product.dosage_form || fallback?.form || "Product",
      pricePerUnit: fallback?.pricePerUnit || `${formatMoney(product.sale_price)}/${(product.dosage_form || "unit").toUpperCase()}`,
      accent: fallback?.accent ?? "#eff8ff",
      breadcrumbs: [
        { label: "Home", href: "/" },
        { label: "Categories", href: "/categories" },
        { label: product.category.name, href: `/categories/${product.category.slug}` },
        { label: product.name }
      ],
      composition: product.composition || fallback?.composition || "General care composition",
      deliveryLabel: fallback?.deliveryLabel || "Tomorrow 10 PM",
      updatedOn: fallback?.updatedOn,
      quickLinks: fallback?.quickLinks ?? [
        { id: "uses", label: "Uses" },
        { id: "how-it-works", label: "How it works" },
        { id: "how-to-use", label: "Directions for use" },
        { id: "side-effects", label: "Side effects" },
        { id: "warning-precautions", label: "Warning & precautions" },
        { id: "interactions", label: "Interactions" },
        { id: "synopsis", label: "Synopsis" },
        { id: "useful-tests", label: "Useful diagnostic tests" },
        { id: "faq", label: "FAQs" },
        { id: "learn-more", label: "Learn more" }
      ],
      galleryItems: fallback?.galleryItems ?? buildGalleryItems(product.name, brandName, product.pack_size || "Pack of 1"),
      coupons: fallback?.coupons ?? buildCoupons(formatMoney(product.sale_price)),
      assuranceItems: fallback?.assuranceItems ?? [...buildAssuranceItems()],
      membership: fallback?.membership ?? buildMembership(),
      highlights: fallback?.highlights ?? description.slice(0, 4),
      productHighlights: fallback?.productHighlights ?? description.slice(0, 4),
      description,
      ingredients: fallback?.ingredients ?? [
        product.composition || `${brandName} product composition`,
        "See the pack label for the complete ingredient list."
      ],
      keyUses: fallback?.keyUses ?? [
        `Useful within ${product.category.name.toLowerCase()} care.`,
        "Compare pack, price, and prescription requirement before purchase."
      ],
      howToUse: fallback?.howToUse ?? [
        "Use as directed on the label or by your doctor.",
        "Follow the recommended timing and dosage instructions."
      ],
      safetyInformation: sideEffects,
      additionalInformation: [
        {
          label: "Good to Know",
          bullets: [
            `Category: ${product.category.name}`,
            `Brand: ${brandName}`,
            `Pack size: ${product.pack_size || "See product details"}`,
            `Prescription required: ${product.requires_prescription ? "Yes" : "No"}`
          ]
        },
        {
          label: "Storage",
          bullets: storageInformation
        }
      ],
      faqs: fallback?.faqs ?? [
        {
          question: `What is ${product.name} used for?`,
          answer: `${product.name} is part of the ${product.category.name.toLowerCase()} catalog and should be reviewed along with its pack details, composition, and prescription requirement before purchase.`
        },
        {
          question: "Can I compare substitutes or alternatives?",
          answer:
            related.length > 0
              ? "Yes. Substitute and related options are shown lower on the page."
              : "Related alternatives will appear here once substitute products are linked in the catalog."
        }
      ],
      warningCards: fallback?.warningCards ?? buildWarningCards(warnings, product.name),
      interactions: fallback?.interactions ?? buildInteractions([
        {
          label: "Good to Know",
          bullets: [
            `Category: ${product.category.name}`,
            `Brand: ${brandName}`,
            `Pack size: ${product.pack_size || "See product details"}`,
            `Prescription required: ${product.requires_prescription ? "Yes" : "No"}`
          ]
        },
        {
          label: "Storage",
          bullets: storageInformation
        }
      ]),
      usefulTests:
        fallback?.usefulTests ??
        buildUsefulTests(
          product.name,
          product.composition || fallback?.composition || "General care composition",
          fallback?.keyUses ?? [
            `Useful within ${product.category.name.toLowerCase()} care.`,
            "Compare pack, price, and prescription requirement before purchase."
          ]
        ),
      synopsis:
        fallback?.synopsis ??
        buildSynopsis({
          composition: product.composition || fallback?.composition || "General care composition",
          brand: brandName,
          keyUses:
            fallback?.keyUses ?? [
              `Useful within ${product.category.name.toLowerCase()} care.`,
              "Compare pack, price, and prescription requirement before purchase."
            ],
          form: product.dosage_form || fallback?.form || "Product"
        }),
      manufacturerDetails: fallback?.manufacturerDetails ?? defaultManufacturerDetails,
      certifiedContent: fallback?.certifiedContent ?? defaultCertifiedContent,
      rails: {
        related,
        manufacturerMore,
        topSelling
      },
      articleLinks: getContextualArticleLinks(product.category.name),
      textLinkSections: getContextualTextLinkSections(product.category.name),
      disclaimer: fallback?.disclaimer ?? [
        "This product information supports browsing and should not replace professional medical advice or pack instructions."
      ]
    } satisfies CatalogProductDetail;
  } catch {
    return getCatalogProductBySlug(slug);
  }
}

export function getFallbackCatalogProduct(slug: string) {
  return (
    getCatalogProductBySlug(slug) ?? {
      slug,
      name: titleFromSlug(slug),
        brand: "TrueCare",
        manufacturer: "TrueCare Health",
      off: "10% OFF",
      mrp: "399",
      price: "359",
      pack: "Pack of 1",
      form: "Product",
      pricePerUnit: "359/UNIT",
      accent: "#f4f0ff",
      breadcrumbs: [
        { label: "Home", href: "/" },
        { label: "Categories", href: "/categories" },
        { label: titleFromSlug(slug) }
      ],
      composition: "General care composition",
      deliveryLabel: "Tomorrow 10 PM",
      quickLinks: [
        { id: "uses", label: "Uses" },
        { id: "how-it-works", label: "How it works" },
        { id: "how-to-use", label: "Directions for use" },
        { id: "side-effects", label: "Side effects" },
        { id: "warning-precautions", label: "Warning & precautions" },
        { id: "interactions", label: "Interactions" },
        { id: "synopsis", label: "Synopsis" },
        { id: "useful-tests", label: "Useful diagnostic tests" },
        { id: "faq", label: "FAQs" },
        { id: "learn-more", label: "Learn more" }
      ],
        galleryItems: buildGalleryItems(titleFromSlug(slug), "TrueCare", "Pack of 1"),
      coupons: buildCoupons("359"),
      assuranceItems: [...buildAssuranceItems()],
      membership: buildMembership(),
      highlights: ["This is a reusable fallback product detail page.", "The layout stays consistent across the catalog."],
      productHighlights: ["This is a reusable fallback product detail page.", "The layout stays consistent across the catalog."],
      description: ["This product page is generated from the shared detail renderer and keeps the same Truemeds-style structure throughout the app."],
      ingredients: ["See packaging for exact ingredients."],
      keyUses: ["Use this page to review product details before purchase."],
      howToUse: ["Follow pack directions."],
      safetyInformation: ["Read the label before use."],
      additionalInformation: [{ label: "Good to Know", bullets: ["Shared detail page layout", "Reusable across the storefront"] }],
      faqs: [{ question: "Why is this page shown?", answer: "This is the reusable fallback view for product detail routes that are not part of the seeded dataset." }],
      warningCards: buildWarningCards(["Read the label before use."], titleFromSlug(slug)),
      interactions: ["Consult the product label and a healthcare professional before combining this product with other care routines."],
      usefulTests: buildUsefulTests(titleFromSlug(slug), "General care composition", ["Use this page to review product details before purchase."]),
      synopsis: buildSynopsis({
        composition: "General care composition",
          brand: "TrueCare",
          keyUses: ["Use this page to review product details before purchase."],
          form: "Product"
        }),
        manufacturerDetails: defaultManufacturerDetails,
        certifiedContent: defaultCertifiedContent,
        rails: emptyRails(),
      articleLinks: getContextualArticleLinks("General Medicines"),
      textLinkSections: getContextualTextLinkSections("General Medicines"),
      disclaimer: [
        "This fallback page is for catalog continuity and should not replace package instructions or professional guidance."
      ]
    } satisfies CatalogProductDetail
  );
}
