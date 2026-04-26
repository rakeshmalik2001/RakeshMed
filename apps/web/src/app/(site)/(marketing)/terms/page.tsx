import { MarketingContentPage } from "@/components/marketing-content-page";
import { marketingPageContent } from "@/lib/storefront-content";

export default function TermsPage() {
  return <MarketingContentPage slug="Terms" content={marketingPageContent.terms} />;
}
