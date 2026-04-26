import { MarketingContentPage } from "@/components/marketing-content-page";
import { marketingPageContent } from "@/lib/storefront-content";

export default function AboutPage() {
  return <MarketingContentPage slug="About" content={marketingPageContent.about} />;
}
