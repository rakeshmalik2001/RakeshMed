import { MarketingContentPage } from "@/components/marketing-content-page";
import { buildEditorialPageContent } from "@/lib/storefront-content";

type HealthGuidePageProps = {
  params: Promise<{
    slug?: string[];
  }>;
};

export default async function HealthGuidePage({ params }: HealthGuidePageProps) {
  const { slug } = await params;
  const content = buildEditorialPageContent("health-guide", slug);

  return <MarketingContentPage slug="Health Guide" content={content} />;
}
