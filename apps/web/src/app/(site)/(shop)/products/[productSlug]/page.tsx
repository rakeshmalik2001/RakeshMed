import { redirect } from "next/navigation";

export default async function ProductDetailRedirect({
  params
}: {
  params: Promise<{ productSlug: string }>;
}) {
  const { productSlug } = await params;

  redirect(`/medicine/${productSlug}`);
}
