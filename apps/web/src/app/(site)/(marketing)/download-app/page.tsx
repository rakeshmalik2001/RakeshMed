import { MarketingContentPage } from "@/components/marketing-content-page";
import { marketingPageContent } from "@/lib/storefront-content";

export default function DownloadAppPage() {
  return <MarketingContentPage slug="Download App" content={marketingPageContent["download-app"]} />;
}
