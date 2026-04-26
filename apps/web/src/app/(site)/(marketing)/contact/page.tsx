import { MarketingContentPage } from "@/components/marketing-content-page";
import { marketingPageContent } from "@/lib/storefront-content";

export default function ContactPage() {
  return <MarketingContentPage slug="Contact" content={marketingPageContent.contact} />;
}
