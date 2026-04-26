import { notFound } from "next/navigation";

import { CategoryCollectionPage } from "@/components/category-collection-page";
import { resolveCategoryPageLive } from "@/lib/category-page-data";

type CategorySubcategoryPageProps = {
  params: Promise<{
    categorySlug: string;
    subcategorySlug: string;
  }>;
};

export default async function CategorySubcategoryPage({ params }: CategorySubcategoryPageProps) {
  const { categorySlug, subcategorySlug } = await params;
  const page = await resolveCategoryPageLive([categorySlug, subcategorySlug]);

  if (!page) {
    notFound();
  }

  return <CategoryCollectionPage {...page} />;
}
