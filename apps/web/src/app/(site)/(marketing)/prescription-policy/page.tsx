import { MarketingContentPage } from "@/components/marketing-content-page";
import { marketingPageContent } from "@/lib/storefront-content";

export default function PrescriptionPolicyPage() {
  return (
    <MarketingContentPage
      slug="Prescription Policy"
      content={marketingPageContent["prescription-policy"]}
    />
  );
}
