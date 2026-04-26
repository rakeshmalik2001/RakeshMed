export type StorefrontProduct = {
  slug: string;
  name: string;
  off: string;
  mrp: string;
  price: string;
  brand: string;
  salt: string;
  category: string;
  form: string;
  useFor: string;
  tags: string[];
  meta: string;
  rx: boolean;
  pack: string;
  uses: string[];
};

export const storefrontProducts: StorefrontProduct[] = [
  {
    slug: "atorva-10-tablet",
    name: "Atorva 10 Tablet",
    off: "38% OFF",
    mrp: "152.40",
    price: "94.48",
    brand: "Zydus",
    salt: "Atorvastatin",
    category: "heart-care",
    form: "Tablet",
    useFor: "Heart Care",
    tags: ["Same salt", "Best savings", "Prescription only", "In stock"],
    meta: "Atorvastatin | Strip of 15 tablets",
    rx: true,
    pack: "Strip of 15 tablets",
    uses: ["Helps lower LDL cholesterol", "Supports cardiovascular risk management"]
  },
  {
    slug: "atorfit-10-tablet",
    name: "Atorfit 10 Tablet",
    off: "42% OFF",
    mrp: "142.90",
    price: "82.88",
    brand: "Sun Pharma",
    salt: "Atorvastatin",
    category: "heart-care",
    form: "Tablet",
    useFor: "Heart Care",
    tags: ["Same salt", "Best savings", "In stock"],
    meta: "Atorvastatin | Strip of 10 tablets",
    rx: true,
    pack: "Strip of 10 tablets",
    uses: ["Alternative same-salt cholesterol medicine", "Supports prescribed lipid control"]
  },
  {
    slug: "aztor-10-tablet",
    name: "Aztor 10 Tablet",
    off: "28% OFF",
    mrp: "151.10",
    price: "108.79",
    brand: "Cipla",
    salt: "Atorvastatin",
    category: "heart-care",
    form: "Tablet",
    useFor: "Heart Care",
    tags: ["Same salt", "Prescription only", "In stock"],
    meta: "Atorvastatin | Strip of 15 tablets",
    rx: true,
    pack: "Strip of 15 tablets",
    uses: ["Helps reduce cholesterol", "Often prescribed with diet and exercise changes"]
  },
  {
    slug: "storvas-10-tablet",
    name: "Storvas 10 Tablet",
    off: "33% OFF",
    mrp: "146.00",
    price: "97.82",
    brand: "Abbott",
    salt: "Atorvastatin",
    category: "heart-care",
    form: "Tablet",
    useFor: "Heart Care",
    tags: ["Same salt", "In stock"],
    meta: "Atorvastatin | Strip of 10 tablets",
    rx: true,
    pack: "Strip of 10 tablets",
    uses: ["Supports cholesterol management", "Prescription-based long-term therapy"]
  },
  {
    slug: "rosuvas-10-tablet",
    name: "Rosuvas 10 Tablet",
    off: "19% OFF",
    mrp: "154.80",
    price: "125.38",
    brand: "Sun Pharma",
    salt: "Rosuvastatin",
    category: "heart-care",
    form: "Tablet",
    useFor: "Heart Care",
    tags: ["Prescription only", "In stock"],
    meta: "Rosuvastatin | Strip of 10 tablets",
    rx: true,
    pack: "Strip of 10 tablets",
    uses: ["Helps control cholesterol", "Used for long-term cardiovascular care"]
  },
  {
    slug: "seven-seas-original-capsule-100",
    name: "Seven Seas Original Capsule 100",
    off: "20% OFF",
    mrp: "398.16",
    price: "318.53",
    brand: "Seven Seas",
    salt: "Omega 3 Fatty Acids",
    category: "vitamins-supplements",
    form: "Capsule",
    useFor: "Vitamins",
    tags: ["Best savings", "In stock"],
    meta: "Wellness supplement | Bottle pack",
    rx: false,
    pack: "Bottle of 100 capsules",
    uses: ["Supports heart wellness", "Daily nutritional supplementation"]
  },
  {
    slug: "limcee-orange-tablet-15",
    name: "Limcee Orange Tablet 15",
    off: "20% OFF",
    mrp: "24.68",
    price: "19.74",
    brand: "Abbott",
    salt: "Vitamin C",
    category: "vitamins-supplements",
    form: "Tablet",
    useFor: "Vitamins",
    tags: ["In stock", "Best savings"],
    meta: "Vitamin C | Chewable tablets",
    rx: false,
    pack: "Strip of 15 tablets",
    uses: ["Daily vitamin support", "Immune wellness support"]
  },
  {
    slug: "electral-sachet-4-4gm",
    name: "Electral Sachet 4.4gm",
    off: "20% OFF",
    mrp: "4.65",
    price: "3.72",
    brand: "Fdc",
    salt: "Electrolytes",
    category: "health-conditions",
    form: "Powder",
    useFor: "Hydration Support",
    tags: ["OTC", "In stock", "Best savings"],
    meta: "Oral rehydration | Single sachet",
    rx: false,
    pack: "Single sachet",
    uses: ["Helps with dehydration support", "Useful during fluid loss recovery"]
  },
  {
    slug: "codvel-capsule-100",
    name: "Codvel Capsule 100",
    off: "40% OFF",
    mrp: "350.00",
    price: "210.00",
    brand: "Cadvel",
    salt: "Cod Liver Oil",
    category: "vitamins-supplements",
    form: "Capsule",
    useFor: "Vitamins",
    tags: ["Best savings", "In stock"],
    meta: "Cod liver oil | Bottle pack",
    rx: false,
    pack: "Bottle of 100 capsules",
    uses: ["Supports wellness supplementation", "Daily nutrition support"]
  },
  {
    slug: "accu-chek-active-test-strip-50",
    name: "Accu-Chek Active Test Strip 50",
    off: "12% OFF",
    mrp: "1095.00",
    price: "963.60",
    brand: "Accu-Chek",
    salt: "Blood Glucose Test Strip",
    category: "diabetes-care",
    form: "Test Strip",
    useFor: "Diabetes Care",
    tags: ["Popular", "In stock"],
    meta: "Blood glucose monitoring | Box of 50 strips",
    rx: false,
    pack: "Box of 50 test strips",
    uses: ["Helps monitor blood glucose at home", "Useful for routine diabetes tracking"]
  },
  {
    slug: "contour-plus-test-strip-50",
    name: "Contour Plus Test Strip 50",
    off: "10% OFF",
    mrp: "975.00",
    price: "877.50",
    brand: "Contour",
    salt: "Blood Glucose Test Strip",
    category: "diabetes-care",
    form: "Test Strip",
    useFor: "Diabetes Care",
    tags: ["Popular", "In stock"],
    meta: "Blood glucose monitoring | Box of 50 strips",
    rx: false,
    pack: "Box of 50 test strips",
    uses: ["Supports daily sugar monitoring", "Useful for repeat diabetes checks"]
  },
  {
    slug: "dr-morepen-bp02-bp-monitor",
    name: "Dr Morepen BP 02 Blood Pressure Monitor",
    off: "18% OFF",
    mrp: "1899.00",
    price: "1557.18",
    brand: "Dr Morepen",
    salt: "Digital Blood Pressure Monitor",
    category: "healthcare-devices",
    form: "Device",
    useFor: "Healthcare Devices",
    tags: ["Popular", "In stock"],
    meta: "Home monitoring device | Single unit",
    rx: false,
    pack: "Single monitoring device",
    uses: ["Helps track blood pressure at home", "Useful for routine cardiovascular monitoring"]
  },
  {
    slug: "omron-ne-c101-nebulizer",
    name: "Omron NE C101 Nebulizer",
    off: "15% OFF",
    mrp: "1999.00",
    price: "1699.15",
    brand: "Omron",
    salt: "Compressor Nebulizer",
    category: "healthcare-devices",
    form: "Device",
    useFor: "Respiratory Support",
    tags: ["Popular", "In stock"],
    meta: "Respiratory support device | Single unit",
    rx: false,
    pack: "Single nebulizer unit",
    uses: ["Supports at-home nebulization", "Useful for respiratory care routines"]
  }
];

const curatedSearchSuggestions = [
  "atorva 10 tablet",
  "atorvastatin",
  "rosuvastatin",
  "vitamin c tablets",
  "electral sachet",
  "glucometer strips",
  "blood pressure monitor",
  "nebulizer machine",
  "cholesterol medicine",
  "diabetes care"
] as const;

export const searchSuggestions = Array.from(new Set(curatedSearchSuggestions));

export function getProductBySlug(slug: string) {
  return storefrontProducts.find((product) => product.slug === slug);
}

export function getProductsByCategory(category: string) {
  return storefrontProducts.filter((product) => product.category === category);
}

export function getRelatedProducts(product: StorefrontProduct, limit = 3) {
  return storefrontProducts
    .filter(
      (candidate) =>
        candidate.slug !== product.slug &&
        (candidate.salt === product.salt || candidate.category === product.category)
    )
    .slice(0, limit);
}
