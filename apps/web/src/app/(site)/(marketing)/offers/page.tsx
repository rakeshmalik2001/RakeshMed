import { MarketingContentPage } from "@/components/marketing-content-page";
import { marketingPageContent } from "@/lib/storefront-content";

export default function OffersPage() {
  return <MarketingContentPage slug="Offers" content={marketingPageContent.offers} />;
}
