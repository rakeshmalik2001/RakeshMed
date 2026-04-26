import { notFound } from "next/navigation";

import { CategoryCollectionPage } from "@/components/category-collection-page";
import { resolveCategoryPageLive } from "@/lib/category-page-data";

type CategoryItemPageProps = {
  params: Promise<{
    categorySlug: string;
    subcategorySlug: string;
    itemSlug: string;
  }>;
};

export default async function CategoryItemPage({ params }: CategoryItemPageProps) {
  const { categorySlug, subcategorySlug, itemSlug } = await params;
  const page = await resolveCategoryPageLive([categorySlug, subcategorySlug, itemSlug]);

  if (!page) {
    notFound();
  }

  return <CategoryCollectionPage {...page} />;
}
