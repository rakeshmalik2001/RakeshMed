import { MarketingContentPage } from "@/components/marketing-content-page";
import { marketingPageContent } from "@/lib/storefront-content";

export default function PrivacyPage() {
  return <MarketingContentPage slug="Privacy" content={marketingPageContent.privacy} />;
}
