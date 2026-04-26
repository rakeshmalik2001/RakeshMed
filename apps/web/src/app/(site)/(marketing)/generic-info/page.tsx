import { MarketingContentPage } from "@/components/marketing-content-page";
import { marketingPageContent } from "@/lib/storefront-content";

export default function GenericInfoPage() {
  return <MarketingContentPage slug="Generic Info" content={marketingPageContent["generic-info"]} />;
}
