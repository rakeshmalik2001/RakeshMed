import { MarketingContentPage } from "@/components/marketing-content-page";
import { marketingPageContent } from "@/lib/storefront-content";

export default function ServiceabilityPage() {
  return (
    <MarketingContentPage
      slug="Serviceability"
      content={marketingPageContent.serviceability}
    />
  );
}
