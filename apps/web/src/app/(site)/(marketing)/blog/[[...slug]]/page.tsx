import { MarketingContentPage } from "@/components/marketing-content-page";
import { buildEditorialPageContent } from "@/lib/storefront-content";

type BlogPageProps = {
  params: Promise<{
    slug?: string[];
  }>;
};

export default async function BlogPage({ params }: BlogPageProps) {
  const { slug } = await params;
  const content = buildEditorialPageContent("blog", slug);

  return <MarketingContentPage slug="Blog" content={content} />;
}
