import { MarketingContentPage } from "@/components/marketing-content-page";
import { marketingPageContent } from "@/lib/storefront-content";

export default function FaqPage() {
  return <MarketingContentPage slug="FAQ" content={marketingPageContent.faq} />;
}
