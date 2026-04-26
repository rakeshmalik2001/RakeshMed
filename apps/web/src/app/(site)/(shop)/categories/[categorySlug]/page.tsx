import { notFound } from "next/navigation";

import { CategoryCollectionPage } from "@/components/category-collection-page";
import { resolveCategoryPageLive } from "@/lib/category-page-data";

type CategoryDetailPageProps = {
  params: Promise<{
    categorySlug: string;
  }>;
};

export default async function CategoryDetailPage({ params }: CategoryDetailPageProps) {
  const { categorySlug } = await params;
  const page = await resolveCategoryPageLive([categorySlug]);

  if (!page) {
    notFound();
  }

  return <CategoryCollectionPage {...page} />;
}
