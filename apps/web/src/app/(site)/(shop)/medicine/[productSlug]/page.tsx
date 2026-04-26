import { notFound } from "next/navigation";

import { MedicineProductPage } from "@/components/medicine-product-page";
import { getLiveCatalogProductBySlug } from "@/lib/catalog-product-data";

export default async function MedicineDetailRoute({
  params
}: {
  params: Promise<{ productSlug: string }>;
}) {
  const { productSlug } = await params;
  const product = await getLiveCatalogProductBySlug(productSlug);

  if (!product) {
    notFound();
  }

  return <MedicineProductPage product={product} />;
}
